import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from PySide6.QtCore import Qt, QProcess, QTimer, QUrl, QSize
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QScrollArea, QStackedWidget, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem)
from . import VERSION
from .paths import ROOT, DATA, DEFAULT_OUTPUT, engine_dir, write_json

CSS = '''
QWidget {font-family:SUIT; font-size:14px; color:#182c44;}
QMainWindow, QWidget#workspace {background:#edf1f5;}
QWidget#rail {background:#14273e;} QWidget#rail QLabel {color:#cbd7e4;}
QLabel#brand {color:white;font-size:24px;font-weight:600;}
QLabel#eyebrow {color:#8fa5bd;font-size:11px;letter-spacing:2px;}
QLabel#muted {color:#667b91;font-size:12px;}
QLabel#heading {font-size:23px;font-weight:600;}
QLabel#subheading {font-size:17px;font-weight:600;}
QLabel#emptytitle {font-size:25px;font-weight:600;}
QLabel#status {background:#e7eef6;border-radius:6px;padding:6px 10px;font-weight:600;}
QFrame#inspector {background:white;border-left:1px solid #d8e1eb;}
QFrame#line {background:#dfe6ef;max-height:1px;}
QPushButton {background:white;border:1px solid #c7d2df;border-radius:7px;padding:10px 14px;font-weight:600;}
QPushButton:hover {background:#eaf0f7;border-color:#8a9fb8;}
QPushButton:pressed {background:#dbe5f1;}
QPushButton:focus {border:2px solid #4e8ac7;}
QPushButton:disabled {background:#eff2f6;color:#99a7b8;border-color:#e1e6ed;}
QPushButton#primary {background:#f88922;color:#17263a;border:1px solid #f88922;}
QPushButton#primary:hover {background:#ff9c43;}
QPushButton#open {background:#143e68;color:white;border-color:#143e68;}
QPushButton#open:disabled {background:#e1e7ef;color:#8b9caf;border-color:#e1e7ef;}
QPushButton#railbutton {background:#203952;color:#e0e9f2;border-color:#3b536d;font-size:12px;}
QPushButton#toggle {padding:6px 12px;font-size:12px;}
QPushButton#toggle:checked {background:#173e67;color:white;border-color:#173e67;}
QListWidget {background:transparent;border:0;outline:0;}
QListWidget::item {margin:3px 0;padding:10px 8px;border-radius:7px;color:#dce6f1;}
QListWidget::item:selected {background:#2b4662;color:white;}
QListWidget::item:hover {background:#203a54;}
QTabWidget::pane {border:0;}
QTabBar::tab {padding:9px 12px;color:#738397;border-bottom:2px solid transparent;}
QTabBar::tab:selected {color:#173e67;border-bottom:2px solid #f88922;font-weight:600;}
QScrollArea {border:0;background:white;}
QScrollArea > QWidget > QWidget {background:white;}
QTreeWidget {border:0;font-size:12px;background:white;}
QTreeWidget::item {padding:5px 0;}
QProgressBar {height:7px;border:0;border-radius:3px;background:#dae3ed;}
QProgressBar::chunk {background:#f88922;border-radius:3px;}
QSplitter::handle {background:#dde5ee;width:1px;}
'''


def label(text='', name=None, wrap=False):
    w=QLabel(text); w.setTextFormat(Qt.PlainText)
    if name: w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text, callback, name=None):
    w=QPushButton(text); w.setCursor(Qt.PointingHandCursor); w.clicked.connect(callback)
    if name: w.setObjectName(name)
    return w


class Preview(QWidget):
    def __init__(self):
        super().__init__(); self.pix=QPixmap(); self.setMinimumSize(200,240)
    def show_file(self,path):
        self.pix=QPixmap(str(path)) if path and Path(path).is_file() else QPixmap(); self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor('#e7ecf2'))
        if self.pix.isNull():
            p.setRenderHint(QPainter.Antialiasing)
            x=self.width()/2; y=self.height()/2-70
            p.setPen(QPen(QColor('#98aabd'),2)); p.setBrush(QColor('#f6f8fb'))
            p.drawRoundedRect(int(x-40),int(y-48),80,96,8,8)
            p.setPen(QColor('#183c61')); f=QFont('SUIT',16); f.setWeight(QFont.DemiBold); p.setFont(f)
            p.drawText(int(x-40),int(y-48),80,96,Qt.AlignCenter,'PSD')
            p.setFont(QFont('SUIT',17)); p.drawText(20,int(y+80),self.width()-40,38,Qt.AlignCenter,'PSD를 여기에 놓으세요')
            p.setFont(QFont('SUIT',11)); p.setPen(QColor('#667b91'))
            p.drawText(20,int(y+121),self.width()-40,55,Qt.AlignCenter|Qt.TextWordWrap,'원본을 보존하고, PhotoCraft에서\n다시 편집할 작업본을 준비합니다.')
            return
        for y in range(0,self.height(),20):
            for x in range(0,self.width(),20):
                if (x//20+y//20)%2: p.fillRect(x,y,20,20,QColor('#f4f6f9'))
        size=self.pix.size(); size.scale(self.width()-40,self.height()-40,Qt.KeepAspectRatio)
        x=(self.width()-size.width())//2; y=(self.height()-size.height())//2
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(x,y,size.width(),size.height(),self.pix)


class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('PSD Bridge — PhotoCraft 작업 준비')
        self.resize(1320,860); self.setMinimumSize(1020,700); self.setAcceptDrops(True)
        DATA.mkdir(parents=True,exist_ok=True)
        try: self.settings=json.loads((DATA/'settings.json').read_text(encoding='utf-8'))
        except (OSError,ValueError): self.settings={}
        self.output=Path(self.settings.get('output',str(DEFAULT_OUTPUT)))
        self.jobs=[]; self.active=None; self.proc=None; self.last_status=''; self.started=0; self.closing=False
        root=QWidget(); layout=QHBoxLayout(root); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0); self.setCentralWidget(root)
        rail=QWidget(); rail.setObjectName('rail'); rail.setFixedWidth(215); rl=QVBoxLayout(rail); rl.setContentsMargins(18,25,18,20); rl.setSpacing(14)
        rl.addWidget(label('CREATIVE HANDOFF','eyebrow')); rl.addWidget(label('PSD Bridge','brand'))
        rl.addWidget(label('익숙한 작업을 이어서.','muted'))
        rl.addSpacing(10); rl.addWidget(button('+  PSD 추가',self.pick,'primary'))
        rl.addWidget(label('작업 목록','eyebrow'))
        self.queue=QListWidget(); self.queue.setSpacing(2); self.queue.currentRowChanged.connect(self.select); rl.addWidget(self.queue,1)
        rl.addWidget(button('저장 위치 변경',self.choose_output,'railbutton'))
        self.output_label=label('저장: '+self.output.name,'muted',True); self.output_label.setToolTip(str(self.output)); rl.addWidget(self.output_label)
        rl.addWidget(label('로컬 처리  ·  v'+VERSION,'eyebrow')); layout.addWidget(rail)
        center=QWidget(); center.setObjectName('workspace'); cl=QVBoxLayout(center); cl.setContentsMargins(24,24,24,16); cl.setSpacing(15)
        cl.addWidget(label('PSD를 이어서 편집하세요','heading'))
        cl.addWidget(label('PSD → 편집 가능한 PhotoCraft 작업본','muted'))
        bar=QHBoxLayout(); self.filename=label('아직 선택한 파일이 없어요','subheading'); self.filename.setMinimumWidth(50); bar.addWidget(self.filename,1)
        self.work_toggle=button('작업본',lambda:self.toggle(False),'toggle'); self.original_toggle=button('원본',lambda:self.toggle(True),'toggle')
        for b in (self.work_toggle,self.original_toggle): b.setCheckable(True); b.setEnabled(False); bar.addWidget(b)
        self.work_toggle.setChecked(True); cl.addLayout(bar)
        self.preview=Preview(); cl.addWidget(self.preview,1)
        self.progress=QProgressBar(); self.progress.setFixedHeight(6); self.progress.setTextVisible(False); self.progress.setValue(0); cl.addWidget(self.progress)
        bottom=QHBoxLayout(); self.message=label('파일을 놓거나 왼쪽의 PSD 추가를 눌러 시작하세요.','muted',True); bottom.addWidget(self.message,1)
        self.cancel=button('중단',self.cancel_active); self.cancel.hide(); bottom.addWidget(self.cancel); cl.addLayout(bottom)
        layout.addWidget(center,1)
        info=QFrame(); info.setObjectName('inspector'); info.setFixedWidth(310); il=QVBoxLayout(info); il.setContentsMargins(20,27,20,20); il.setSpacing(15)
        il.addWidget(label('작업 준비','subheading')); self.badge=label('파일을 기다리고 있어요','status'); il.addWidget(self.badge)
        self.metrics=label('레이어와 글꼴을 확인한 뒤\n편집할 수 있는 작업본을 만들어요.',None,True); il.addWidget(self.metrics)
        self.tabs=QTabWidget(); self.summary=label('',None,True); self.summary.setAlignment(Qt.AlignTop); self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); inner=QWidget(); inn=QVBoxLayout(inner); inn.setContentsMargins(0,14,8,10); inn.addWidget(self.summary); inn.addStretch(); scroll.setWidget(inner)
        self.tabs.addTab(scroll,'검사 결과')
        self.fonts=QTreeWidget(); self.fonts.setHeaderHidden(True); self.fonts.setIndentation(12); self.tabs.addTab(self.fonts,'글꼴')
        self.layerlist=QTreeWidget(); self.layerlist.setHeaderHidden(True); self.layerlist.setIndentation(12); self.tabs.addTab(self.layerlist,'레이어'); il.addWidget(self.tabs,1)
        self.open_button=button('PhotoCraft에서 편집',self.open_editor,'open'); il.addWidget(self.open_button)
        actions=QHBoxLayout(); self.folder_button=button('결과 폴더',self.open_folder); self.report_button=button('검사 보고서',self.open_report); actions.addWidget(self.folder_button); actions.addWidget(self.report_button); il.addLayout(actions)
        self.retry=button('다시 준비',self.retry_selected); il.addWidget(self.retry)
        il.addWidget(label('RGB · 8비트 PSD / 256MB 이하\n글꼴 설치·외부 파일 연결은 별도 확인','muted',True)); layout.addWidget(info)
        QShortcut(QKeySequence.Open,self,activated=self.pick)
        self.timer=QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(250)
        self.display(None)
        for entry in self.settings.get('history',[])[-15:]:
            try:
                r=json.loads(Path(entry).read_text(encoding='utf-8'))
                if r.get('output') and Path(r['output']).is_file(): self.add_job(r['source'],r)
            except (OSError,ValueError): pass

    def current(self):
        i=self.queue.currentRow(); return self.jobs[i] if 0<=i<len(self.jobs) else None
    def save_settings(self):
        self.settings['output']=str(self.output)
        self.settings['history']=[str(Path(j['result']['directory'])/'report.json') for j in self.jobs if j.get('result')][-30:]
        write_json(DATA/'settings.json',self.settings)
    def pick(self):
        names,_=QFileDialog.getOpenFileNames(self,'PSD 파일 추가','','Photoshop 문서 (*.psd)'); self.enqueue(names)
    def choose_output(self):
        value=QFileDialog.getExistingDirectory(self,'작업본 저장 위치',str(self.output if self.output.exists() else Path.home()))
        if value: self.output=Path(value); self.output_label.setText('저장: '+self.output.name); self.output_label.setToolTip(value); self.save_settings()
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(u.isLocalFile() and u.toLocalFile().lower().endswith('.psd') for u in event.mimeData().urls()): event.acceptProposedAction()
    def dropEvent(self,event):
        self.enqueue([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]); event.acceptProposedAction()
    def enqueue(self,names):
        for name in names:
            p=Path(name)
            if p.is_file() and p.suffix.lower()=='.psd': self.add_job(str(p.resolve()))
        self.start_next()
    def add_job(self,name,result=None):
        job={'source':name,'state':result['status'] if result else '대기 중','result':result,'output_root':str(self.output)}
        self.jobs.append(job); item=QListWidgetItem(); item.setSizeHint(QSize(170,65)); self.queue.addItem(item); self.update_item(job)
        self.queue.setCurrentRow(len(self.jobs)-1)
    def update_item(self,job):
        item=self.queue.item(self.jobs.index(job)); name=Path(job['source']).stem
        item.setText((name if len(name)<17 else name[:16]+'…')+'\n'+job['state']); item.setToolTip(Path(job['source']).name+'\n'+job['state'])
    def select(self,index): self.display(self.current())
    def display(self,job):
        r=job.get('result') if job else None; state=job['state'] if job else '파일을 기다리고 있어요'
        self.badge.setText(state); self.badge.setStyleSheet('background:#fff0d9;color:#80511f;' if state=='확인 필요' else 'background:#fbe7e4;color:#8b352c;' if state in ('실패','중단됨') else '')
        self.filename.setText(Path(job['source']).name if job else '아직 선택한 파일이 없어요'); self.filename.setToolTip(job['source'] if job else '')
        self.work_toggle.setEnabled(bool(r)); self.original_toggle.setEnabled(bool(r and r.get('original_preview')))
        self.toggle(False); self.fonts.clear(); self.layerlist.clear()
        for b in (self.open_button,self.folder_button,self.report_button): b.setEnabled(bool(r and Path(r['output']).is_file()))
        self.retry.setEnabled(bool(job and job is not self.active))
        if r:
            d=r['source_document']; self.metrics.setText(f"{d['width']} × {d['height']} px\n레이어 {r['layer_count']}개 · 텍스트 {r['text_count']}개")
            checked='✓ 원본 보존 확인\n✓ 작업본 저장 후 재열기\n✓ 레이어·텍스트 유지'
            checked+='\n✓ 텍스트 수정·재저장 확인' if r['text_count'] else '\n• 편집 가능한 텍스트 없음'
            warnings=r.get('warnings',[])
            self.summary.setText(checked+'\n\n'+('확인할 내용\n\n'+'\n\n'.join('• '+w for w in warnings) if warnings else '자동 검사에서 추가 확인 항목이 발견되지 않았어요.')+'\n\n원본 비교는 PSD에 저장된 미리보기 기준입니다. 모든 효과가 같음을 보증하지 않습니다.')
            for f in r.get('fonts',[]):
                item=QTreeWidgetItem([f['family']+'\n'+f['status']]); item.setToolTip(0,f.get('postscript_name') or str(f.get('weight'))); self.fonts.addTopLevelItem(item)
            if not r.get('fonts'): self.fonts.addTopLevelItem(QTreeWidgetItem(['텍스트 글꼴 없음']))
            for l in d['layers']:
                item=QTreeWidgetItem([l['name']+'\n'+l['kind']]); item.setToolTip(0,l.get('text','')); self.layerlist.addTopLevelItem(item)
        else:
            self.metrics.setText('원본 보존 → 글꼴·레이어 검사\n→ 작업본 저장 → 재열기 검증')
            self.summary.setText(job.get('error','') if job and job['state'] in ('실패','중단됨') else '준비가 끝나면 여기에서 확인할 내용을 볼 수 있어요.\n\n한글 글꼴과 텍스트를 검사하고, PhotoCraft에서 편집할 .pcraft 파일을 별도로 저장합니다.\n\n기존 PSD는 덮어쓰지 않습니다.')
        self.refresh_progress()
    def toggle(self,original):
        self.work_toggle.setChecked(not original); self.original_toggle.setChecked(original)
        j=self.current(); r=j.get('result') if j else None
        self.preview.show_file(r.get('original_preview' if original else 'preview') if r else None)
    def refresh_progress(self):
        self.cancel.setVisible(bool(self.active))
        if self.active:
            self.progress.setValue(self.active.get('percent',2)); self.message.setText(Path(self.active['source']).name+' · '+self.active.get('message','시작하는 중이에요.'))
        else:
            j=self.current(); self.progress.setValue(100 if j and j.get('result') else 0)
            self.message.setText('작업본을 열어 이어서 편집하세요.' if j and j.get('result') else '파일을 놓거나 왼쪽의 PSD 추가를 눌러 시작하세요.')
    def start_next(self):
        if self.active or self.closing: return
        job=next((j for j in self.jobs if j['state']=='대기 중'),None)
        if not job: self.refresh_progress(); return
        self.active=job; job['state']='준비 중'; self.update_item(job)
        base=DATA/'jobs'/uuid.uuid4().hex; config=base.with_suffix('.json'); job['status_file']=str(base.with_suffix('.status.json'))
        write_json(config,{'source':job['source'],'output':job['output_root'],'status':job['status_file']})
        self.proc=QProcess(self); self.proc.setWorkingDirectory(str(ROOT))
        arguments=['--worker',str(config)]
        if not getattr(sys,'frozen',False): arguments=[str(ROOT/'main.py')]+arguments
        self.proc.setProgram(sys.executable); self.proc.setArguments(arguments)
        self.proc.setStandardErrorFile(str(base.with_suffix('.stderr.log'))); self.proc.setStandardOutputFile(str(base.with_suffix('.stdout.log')))
        self.proc.finished.connect(self.finished); self.proc.errorOccurred.connect(self.process_error)
        self.started=time.monotonic(); self.last_status=''; self.proc.start(); self.display(self.current())
    def process_error(self,error):
        if error==QProcess.FailedToStart and self.active:
            self.active['error']='작업 엔진을 시작하지 못했습니다. ZIP을 완전히 풀었는지 확인해 주세요.\n'+self.proc.errorString()
            self.finished(-1,QProcess.CrashExit)
    def poll(self):
        if not self.active: return
        try:
            s=json.loads(Path(self.active['status_file']).read_text(encoding='utf-8'))
            if s.get('state')=='running': self.active.update(percent=s['percent'],message=s['message'])
        except (OSError,ValueError): pass
        self.refresh_progress()
        if time.monotonic()-self.started>600:
            self.active['error']='10분 동안 작업이 끝나지 않아 중단했습니다. 파일 크기와 손상 여부를 확인한 뒤 다시 시도해 주세요.'; self.proc.kill()
    def finished(self,code,status):
        job=self.active
        if not job: return
        try: s=json.loads(Path(job['status_file']).read_text(encoding='utf-8'))
        except (OSError,ValueError): s={}
        if job.get('cancelled'): job.update(state='중단됨',error='사용자가 작업을 중단했습니다. 원본 PSD는 변경하지 않았습니다.')
        elif code==0 and s.get('state')=='done': job.update(state=s['result']['status'],result=s['result'])
        else: job.update(state='실패',error=job.get('error') or s.get('error') or '작업 엔진이 종료되었습니다. 파일이 손상되지 않았는지 확인해 주세요.\n진단 기록: '+str(Path(job['status_file']).parent))
        self.update_item(job); self.active=None
        if self.proc: self.proc.deleteLater(); self.proc=None
        self.save_settings(); self.display(self.current()); QTimer.singleShot(250,self.start_next)
    def cancel_active(self):
        if self.active: self.active['cancelled']=True; self.proc.kill()
    def retry_selected(self):
        j=self.current()
        if j and j is not self.active: self.enqueue([j['source']])
    def open_editor(self):
        j=self.current()
        if not j or not j.get('result'): return
        path=Path(j['result']['output']); exe=engine_dir()/'photocraft.exe'
        try:
            if not path.is_file() or not exe.is_file(): raise FileNotFoundError('작업본 또는 PhotoCraft 실행 파일이 없습니다. ZIP 전체를 다시 풀어 주세요.')
            env=os.environ.copy(); env['PHOTOCRAFT_CONFIG_DIR']=str(DATA/'PhotoCraft')
            preferences=DATA/'PhotoCraft'/'preferences.json'
            if not preferences.exists():
                # An explicit initial CPU preference avoids the recovery modal that
                # --safe-gpu intentionally displays. Later user preferences are kept.
                write_json(preferences,{'performance':{'renderingMode':'cpu','useGpu':False,'gpuBackend':'auto'}})
            # A dedicated instance avoids taking over existing edits.
            log=open(DATA/'photocraft.log','ab')
            process=subprocess.Popen([str(exe),'--new-instance','--',str(path)],cwd=str(engine_dir()),env=env,stdout=log,stderr=log,creationflags=0x08000000)
            log.close(); self.message.setText('PhotoCraft를 여는 중이에요…')
            def check():
                if process.poll() is not None and process.returncode!=0:
                    self.message.setText('PhotoCraft 실행에 실패했습니다. 상세 기록: '+str(DATA/'photocraft.log'))
                else: self.message.setText('PhotoCraft에서 작업본을 열었습니다.')
            QTimer.singleShot(2500,check)
        except OSError as e: self.message.setText(str(e))
    def open_folder(self):
        j=self.current()
        if j and j.get('result'): QDesktopServices.openUrl(QUrl.fromLocalFile(j['result']['directory']))
    def open_report(self):
        j=self.current()
        if j and j.get('result'): QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(j['result']['directory'])/'검사 결과.html')))
    def closeEvent(self,event):
        self.closing=True
        if self.active and self.proc:
            self.active['cancelled']=True; self.proc.kill(); self.proc.waitForFinished(3000)
        self.save_settings(); event.accept()


def run(files=()):
    app=QApplication(sys.argv[:1]); app.setApplicationName('PSD Bridge'); app.setOrganizationName('PSD Bridge')
    for font in ('SUIT-Regular.otf','SUIT-SemiBold.ttf'): QFontDatabase.addApplicationFont(str(ROOT/'assets'/font))
    app.setFont(QFont('SUIT',10)); app.setStyle('Fusion'); app.setStyleSheet(CSS)
    window=Window(); window.show()
    if files: QTimer.singleShot(300,lambda:window.enqueue(files))
    return app.exec()
