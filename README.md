# 암호화폐 트레이딩 분석 및 스크리닝 도구

이 프로젝트는 다양한 암호화폐 스크리닝 전략을 실행하고 시장 데이터를 분석하기 위한 파이썬 기반의 CLI 도구입니다.

## 주요 기능

- **다양한 스크리닝 전략:**
  - `daily`: 일봉 차트의 특정 패턴(예: ATH 대비 하락, 변동성, CCI)을 기반으로 관심 코인을 분석하고 차트를 생성합니다.
  - `altcoin`: 신규 상장, 특정 가격 패턴 등 주어진 조건에 맞는 알트코인을 탐색합니다.
  - `futures`: 바이낸스 선물 시장의 미결제 약정(OI), 롱/숏 비율, 펀딩비 등 데이터를 분석합니다.
  - `daytrade`: 특정 코인에 대해 여러 타임프레임(1D, 4H, 1H, 15m 등)을 종합 분석하여 단기 트레이딩 시그널을 찾거나 전략을 백테스트합니다.
- **모듈화된 구조:** 공통 기능(데이터 fetching, 지표 계산, 차트 생성)이 `utils` 모듈로 분리되어 있어 새로운 스크리닝 전략을 쉽게 추가하고 확장할 수 있습니다.
- **CLI 기반 실행:** `main.py`를 통해 원하는 스크리너와 옵션을 선택하여 간편하게 실행할 수 있습니다.

## 설치 방법

1.  **프로젝트 복제:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **가상 환경 생성 및 활성화 (권장):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # macOS/Linux
    # .\.venv\Scripts\activate  # Windows
    ```

3.  **필요한 라이브러리 설치:**
    ```bash
    pip install -r requirements.txt
    ```

## 사용 방법

이 도구는 웹 UI와 CLI 두 가지 방식으로 사용할 수 있습니다.

### 1. 웹 UI (권장)

간단한 웹 인터페이스를 통해 각 스크리너를 실행하고 결과를 바로 확인할 수 있습니다.

1.  **웹 서버 실행:**
    ```bash
    python main.py web
    ```
2.  웹 브라우저에서 `http://127.0.0.1:8000` 주소로 접속합니다.
3.  드롭다운 메뉴에서 원하는 스크리너를 선택하고 '실행' 버튼을 클릭합니다.

### 2. CLI (명령줄 인터페이스)

터미널에서 직접 스크리너를 실행할 수 있습니다.

```bash
python main.py run [스크리너_이름] [옵션]
```

**스크리너 종류:**

- **`daily`**: 데일리 관심 코인 스크리너
  ```bash
  python main.py run daily
  ```
  - 실행 결과는 `watchlist.txt` 파일과 `charts/` 디렉토리에 저장됩니다.

- **`altcoin`**: 특정 패턴 알트코인 탐색
  ```bash
  python main.py run altcoin
  ```

- **`futures`**: 바이낸스 선물 시장 분석
  ```bash
  python main.py run futures
  ```

- **`daytrade`**: 단타 전략 분석 및 백테스트
  - 실시간 분석 모드 (기본값):
    ```bash
    python main.py run daytrade
    ```
  - 백테스트 모드:
    ```bash
    python main.py run daytrade --mode backtest
    ```
  - 분석 대상 심볼은 `config.json` 파일의 `DAY_TRADING_SYMBOL` 값을 수정하여 변경할 수 있습니다.

## 설정

- `config.json`: 프로젝트의 주요 설정을 담고 있습니다. `daytrade` 스크리너의 분석 대상 심볼(`DAY_TRADING_SYMBOL`) 등을 여기서 변경할 수 있습니다.
  - `config.json.example` 파일을 `config.json`으로 복사한 후, 필요에 따라 값을 수정하여 사용하세요.
- 각 `screener/` 안의 파이썬 파일 상단에서 해당 스크리너의 세부 분석 기준(예: CCI 기간, 변동성 기준 등)을 직접 수정할 수 있습니다.

## 테스트 실행

프로젝트의 테스트는 `unittest` 프레임워크를 사용하여 작성되었습니다. 다음 명령어를 통해 모든 테스트를 실행할 수 있습니다:

```bash
python -m unittest discover tests
```

## 코드 스타일

이 프로젝트는 [Black](https://github.com/psf/black)과 [Flake8](https://flake8.pycqa.org/en/latest/)을 사용하여 코드 스타일을 관리합니다. 코드를 커밋하기 전에 다음 명령어를 실행하여 코드 스타일을 확인하고 자동으로 포맷팅하는 것을 권장합니다.

```bash
black .
flake8 .
```

## 기여 방법

이 프로젝트는 오픈소스이며, 여러분의 기여를 환영합니다. 버그를 발견하거나 새로운 기능을 제안하고 싶다면 언제든지 이슈(Issue)를 등록하거나 풀 리퀘스트(Pull Request)를 보내주세요.

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)를 따릅니다.