# PSD Bridge

**PSD를 넣고, PhotoCraft에서 이어서 편집하세요.**

Windows용 오프라인 작업 준비 도구입니다. PSD를 검사하고 원본과 별개인 `.pcraft` 작업본을 만듭니다. 저장한 파일을 다시 열어 레이어와 텍스트를 확인하고, 글꼴 누락이나 외관 차이를 보고합니다. AI 계정, API 키, Photoshop 설치가 필요하지 않습니다.

## 설치와 사용

1. [최신 배포](https://github.com/duct-tape2/psd-bridge/releases/latest)에서 **`PSD-Bridge-0.1.0-Setup.zip` 하나만** 받습니다.
2. ZIP **전체를** 쓰기 가능한 폴더에 풉니다. ZIP 안에서 바로 실행하지 마세요.
3. `START.bat`를 실행합니다. 첫 실행에만 약 145MB를 자동으로 내려받아 SHA-256을 확인하고 앱을 엽니다. 별도 Python이나 관리자 권한은 필요 없습니다. 이후 PSD 처리는 완전히 오프라인입니다.
4. PSD 파일을 창에 끌어다 놓거나 **PSD 추가**를 누릅니다. 여러 파일을 순서대로 처리합니다.
5. 오른쪽의 검사 결과와 글꼴 목록을 확인합니다. **원본 / 작업본** 버튼으로 미리보기를 비교할 수 있습니다.
6. **PhotoCraft에서 편집**을 누릅니다. 열린 작업본의 글자와 레이어를 수정하고 저장합니다.

처음에는 `samples/새로운 시작.psd`로 시험해 보세요. 회사 자료가 없는 편집 가능한 한국어 예제입니다.

설치 후에는 `PSD-Bridge-0.1.0/PSD-Bridge/PSDBridge.exe`로 바로 실행할 수 있습니다. BAT 옆에 생성되는 `PSD-Bridge-0.1.0-Windows-x64.zip` 전체를 다른 PC로 옮기면, 인터넷 없이 압축을 풀고 실행할 수 있습니다. 릴리스의 `.part01` 등은 설치 BAT가 자동으로 받는 분할 파일이므로 직접 받을 필요가 없습니다.

Windows 10/11 x64용입니다. 첫 버전 실행 파일은 코드 서명되어 있지 않습니다. 회사의 실행 정책으로 차단되는 경우 담당 관리자에게 승인 여부를 확인하세요.

## 결과물

기본 저장 위치는 사용자 문서 폴더의 `PSD Bridge/작업본/YYMMDD/파일명_시간_고유번호/`입니다. 왼쪽 **저장 위치 변경**으로 바꿀 수 있습니다.

| 파일 | 용도 |
|---|---|
| `원본.psd` | 원본과 SHA-256이 같은 보존 복사본 |
| `파일명.pcraft` | PhotoCraft에서 편집할 작업본 |
| `작업본 미리보기.png` | 작업본 표시 확인 |
| `원본 저장 미리보기.png` | PSD에 합성 미리보기가 있는 경우 |
| `검사 결과.html`, `report.json` | 글꼴·확인 사항·검증 결과 |

원본 PSD는 덮어쓰지 않습니다. 같은 이름을 여러 번 처리해도 별도 결과 폴더가 만들어집니다. 중단되거나 실패한 작업의 부분 파일이 결과 폴더에 남을 수 있으나 완료 목록으로 표시하지 않습니다.

## 첫 버전 지원 범위

- RGB, 8비트 PSD / 최대 256 MiB / 3,200만 화소 / 한 변 16,000px / 레이어 500개
- 레이어 이름·순서·그룹·표시 상태와 편집 가능한 텍스트의 가져오기 검사
- `.pcraft` 저장 후 레이어 구조와 텍스트 스타일 재확인
- 별도 검사용 복사본에서 실제 텍스트 수정 → 저장 → 재열기 검사
- 설치된 글꼴의 패밀리·PostScript 이름·굵기 확인
- 저장된 원본 미리보기와 작업본 비교, 텍스트 재계산 시 변화 감지
- PhotoCraft 0.11.1 동봉, 오프라인 처리, 파일별 작업 격리·중단·재시도

**‘준비 완료’는 정해진 자동 검사를 통과했다는 의미이며 Photoshop과 모든 요소가 동일하다는 보증이 아닙니다.** 원본과의 외관 비교는 PSD에 저장된 합성 미리보기 기준입니다. Photoshop을 실행해 재렌더링한 결과가 아닙니다. 원본 미리보기가 오래된 경우에도 그 한계가 있습니다.

**‘확인 필요’** 파일도 작업본을 열 수 있습니다. 다음 사항을 확인하세요.

- **글꼴 누락:** 합법적으로 보유한 정확한 글꼴과 굵기를 설치하고, 앱의 **다시 준비**로 원본에서 새 작업본을 만드세요. 글꼴을 무단 추출하거나 자동 설치하지 않습니다. PhotoCraft 자체 대체 표시로 모양이 달라질 수 있습니다.
- **효과·스마트 오브젝트·마스크:** PhotoCraft 지원 범위에 따라 표시나 세부 편집 방식이 다를 수 있습니다. 전체 레이어가 있는 것만으로 내부 필터까지 보존되었다고 판정하지 않습니다.
- **외부 연결 파일:** 연결 자원의 존재를 보고하지만 자동 수집·경로 복구는 아직 지원하지 않습니다. 원본 PSD 복사본만으로 완전한 자원 백업이 되지는 않습니다.
- **CMYK, 16/32비트, PSB:** 첫 버전에서 거부합니다. Photoshop에서 원본을 보존한 별도 RGB 8비트 PSD를 준비하세요.

Premiere, 다중 편집기, 글꼴 다운로드, 새 이미지 생성은 이 버전에 포함하지 않습니다.

## 실행 문제

- 실행 파일만 옮기지 말고 `_internal`, `vendor`, `assets`를 포함한 전체 폴더를 옮기세요.
- 프로그램 자체가 시작하지 않으면 `%LOCALAPPDATA%/PSDBridge/startup.log`를 확인하세요.
- 작업 실패 기록은 `%LOCALAPPDATA%/PSDBridge/jobs/`, PhotoCraft 실행 기록은 `photocraft.log`에 있습니다.
- PhotoCraft는 별도 인스턴스와 CPU 렌더링으로 실행해 기존 편집 세션과 GPU 호환성 문제를 줄였습니다.
- 기록에는 로컬 파일 경로와 프로젝트 정보가 들어갈 수 있습니다. 공개 이슈에 올리기 전 내용을 확인하세요. 앱은 기록이나 PSD를 외부로 전송하지 않습니다.

## 개발 및 빌드

Python 3.12, Windows x64 기준입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.19.0
.\.venv\Scripts\python.exe tools\fetch_engine.py
.\.venv\Scripts\python.exe tests\make_sample.py
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe tests\integration.py
.\.venv\Scripts\python.exe tools\build.py
.\.venv\Scripts\python.exe tools\package_download.py
```

`tools/fetch_engine.py`는 공식 PhotoCraft v0.11.1 릴리스에서 실행 파일을 가져오고, 저장된 SHA-256과 일치하는지 검사합니다. 다운로드가 필요한 단계는 개발 환경 준비 때뿐입니다.

CLI: `PSDBridge.exe --process input.psd --output output-folder --report result.json`. 성공은 종료 코드 0, 실패는 1입니다. `확인 필요`는 처리 성공이면서 추가 확인이 필요한 상태입니다.

구조: `bridge/inspect_psd.py` 원본 분석, `engine.py` PhotoCraft JSON 프로토콜, `pipeline.py` 변환·검증, `ui.py` Qt 화면과 작업 큐. GUI와 각 파일 처리 프로세스는 분리됩니다. 실행 중인 처리 엔진은 Windows Job Object로 관리합니다.

## 라이선스와 자료

앱 코드는 MIT입니다. PhotoCraft는 별도 프로젝트이며 Adobe 제품이 아닙니다. 번들 구성과 라이선스는 `THIRD_PARTY_NOTICES.md`, `licenses/`, `vendor/photocraft/`를 확인하세요. 회사 템플릿·로고·사용자 작업물·유료 글꼴은 포함하지 않습니다.
