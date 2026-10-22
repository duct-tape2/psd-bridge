import ctypes
import json
import os
import queue
import subprocess
import threading
from .paths import engine_dir


class PhotoCraft:
    """One isolated engine per job. Pipes carry UTF-8; a Windows Job owns children."""
    def __init__(self, workspace):
        cli = engine_dir() / 'photocraft-cli.exe'
        if not cli.is_file():
            raise RuntimeError('PhotoCraft 실행 파일이 없습니다. ZIP 전체를 다시 압축 해제해 주세요.')
        self.process = subprocess.Popen(
            [str(cli), 'serve', '--automation-read-root', str(workspace), '--automation-write-root', str(workspace)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.job = None
        if os.name == 'nt':
            # The job handle is not inherited. If the worker exits or is cancelled,
            # Windows closes it and kills the engine, including hung native calls.
            from ctypes import wintypes as w
            class BASIC(ctypes.Structure):
                _fields_ = [('a', ctypes.c_int64), ('b', ctypes.c_int64), ('flags', w.DWORD), ('min', ctypes.c_size_t), ('max', ctypes.c_size_t), ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
            class IO(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in ['read', 'write', 'other', 'readBytes', 'writeBytes', 'otherBytes']]
            class EXT(ctypes.Structure):
                _fields_ = [('basic', BASIC), ('io', IO), ('processMemory', ctypes.c_size_t), ('jobMemory', ctypes.c_size_t), ('peakProcess', ctypes.c_size_t), ('peakJob', ctypes.c_size_t)]
            k = ctypes.windll.kernel32
            k.CreateJobObjectW.restype = w.HANDLE
            k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
            k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
            k.CloseHandle.argtypes = [w.HANDLE]
            job = k.CreateJobObjectW(None, None)
            limits = EXT(); limits.basic.flags = 0x2000
            if job and k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) and k.AssignProcessToJobObject(job, w.HANDLE(int(self.process._handle))):
                self.job = job
            elif job:
                k.CloseHandle(job)
        self.queue = queue.Queue()
        self.counter = 0
        self.stderr = []
        def read():
            try:
                for line in self.process.stdout:
                    try: self.queue.put(json.loads(line))
                    except ValueError: pass
            finally: self.queue.put(None)
        def errors():
            for line in self.process.stderr:
                self.stderr.append(line[-2000:])
                self.stderr[:] = self.stderr[-30:]
        threading.Thread(target=read, daemon=True).start()
        threading.Thread(target=errors, daemon=True).start()

    def rpc(self, method, **params):
        self.counter += 1
        try:
            self.process.stdin.write(json.dumps({'id': self.counter, 'method': method, 'params': params}, ensure_ascii=False)+'\n')
            self.process.stdin.flush()
            response = self.queue.get(timeout=120)
        except (OSError, queue.Empty) as e:
            raise RuntimeError('PhotoCraft 응답이 없거나 연결이 종료됐습니다. 파일 크기와 형식을 확인하고 다시 시도해 주세요.') from e
        if response is None:
            raise RuntimeError('PhotoCraft가 처리 중 종료됐습니다. 로그를 확인해 주세요. '+''.join(self.stderr)[-500:])
        if response.get('id') != self.counter:
            raise RuntimeError('PhotoCraft 응답 순서가 일치하지 않습니다. 작업을 다시 시작해 주세요.')
        if not response.get('ok'):
            raise RuntimeError(str(response.get('error', 'PhotoCraft 처리 오류')))
        return response.get('result')

    def run(self, command, **params):
        return self.rpc('engine.execute', command=command, params=params)

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.close(); self.process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill(); self.process.wait(timeout=3)
        if self.job:
            ctypes.windll.kernel32.CloseHandle(self.job)
            self.job = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def layers(tree):
    for layer in tree:
        yield layer
        yield from layers(layer.get('children', []))


def structure(tree):
    keys = ('name', 'kind', 'visible', 'opacity', 'blend', 'clipped', 'hasMask', 'hasVectorMask')
    return [{**{k: layer.get(k) for k in keys}, 'text': layer.get('text', {}).get('text'),
             'children': structure(layer.get('children', []))} for layer in tree]
