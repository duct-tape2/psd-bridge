import argparse
import json
import multiprocessing
import sys
import traceback
from pathlib import Path


def worker(config_path):
    from bridge.paths import write_json
    from bridge.pipeline import prepare
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    def progress(percent, message):
        write_json(config['status'], {'state': 'running', 'percent': percent, 'message': message})
    try:
        result = prepare(config['source'], config['output'], progress)
        write_json(config['status'], {'state': 'done', 'percent': 100, 'result': result})
        return 0
    except Exception as exc:
        log = Path(config['status']).with_suffix('.log')
        log.write_text(traceback.format_exc(), encoding='utf-8')
        write_json(config['status'], {'state': 'failed', 'error': str(exc), 'log': str(log)})
        return 1


def main():
    parser = argparse.ArgumentParser(description='PSD Bridge — editable PhotoCraft preparation')
    parser.add_argument('files', nargs='*')
    parser.add_argument('--worker')
    parser.add_argument('--process')
    parser.add_argument('--output')
    parser.add_argument('--report')
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker)
    if args.process:
        from bridge.paths import write_json, DEFAULT_OUTPUT
        from bridge.pipeline import prepare
        try:
            result = prepare(args.process, args.output or DEFAULT_OUTPUT)
            if args.report: write_json(args.report, result)
            if sys.stdout: print(json.dumps(result, ensure_ascii=False))
            return 0
        except Exception as exc:
            if args.report: write_json(args.report, {'status': '실패', 'error': str(exc)})
            if sys.stderr: print(str(exc), file=sys.stderr)
            return 1
    from bridge.ui import run
    return run(args.files)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    try:
        raise SystemExit(main())
    except Exception:
        from bridge.paths import DATA
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA/'startup.log').write_text(traceback.format_exc(), encoding='utf-8')
        # Only interactive startup shows a dialog; a background worker never does.
        if '--worker' not in sys.argv and '--process' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, '프로그램을 시작하지 못했습니다.\nZIP을 완전히 푼 뒤 다시 실행해 주세요.\n\n상세 기록: '+str(DATA/'startup.log'), 'PSD Bridge', 0x10)
        raise SystemExit(1)
