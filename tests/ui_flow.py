"""Exercise the GUI drop event and actual worker, including failure recovery."""
import sys,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QMimeData,QUrl,QPointF
from PySide6.QtGui import QDropEvent
import bridge.ui as ui
from bridge.paths import ROOT

def main():
    app=QApplication([]);app.setStyleSheet(ui.CSS)
    with tempfile.TemporaryDirectory(prefix='bridge-ui-test-') as temp:
        root=Path(temp);ui.DATA=root/'settings';w=ui.Window();w.output=root/'output';w.show()
        bad=root/'손상.psd';bad.write_bytes(b'broken')
        mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(bad)),QUrl.fromLocalFile(str(ROOT/'samples'/'새로운 시작.psd'))])
        event=QDropEvent(QPointF(400,350),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
        w.dropEvent(event)
        deadline=time.monotonic()+60
        while any(j['state'] in ('대기 중','준비 중') for j in w.jobs) and time.monotonic()<deadline:
            app.processEvents();time.sleep(.03)
        assert w.jobs[0]['state']=='실패',w.jobs
        assert w.jobs[1].get('result'),w.jobs
        w.queue.setCurrentRow(0);app.processEvents()
        assert not w.open_button.isEnabled() and w.preview.pix.isNull()
        w.queue.setCurrentRow(1);app.processEvents()
        assert w.open_button.isEnabled() and not w.preview.pix.isNull()
        w.enqueue([str(ROOT/'samples'/'새로운 시작.psd')]);app.processEvents();w.cancel_active()
        deadline=time.monotonic()+10
        while w.active and time.monotonic()<deadline: app.processEvents();time.sleep(.02)
        assert w.jobs[-1]['state']=='중단됨'
        w.close();app.processEvents()
        print('PASS: drag/drop, background worker, failed-file recovery, preview clearing, cancellation')

if __name__=='__main__': main()
