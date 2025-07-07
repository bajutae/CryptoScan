# 암호화폐 스크리너 프로젝트

## 프로젝트 개요

이 프로젝트는 다양한 전략을 사용하여 암호화폐 시장에서 잠재적인 투자 기회를 식별하는 파이썬 기반의 스크리닝 도구 모음입니다. 현재 다음 세 가지 주요 스크리너를 포함하고 있습니다.

1.  **`altcoin_screener.py`**: 특정 패턴(예: MOVE/KRW, IMX/KRW)을 보이는 알트코인을 탐색합니다. 신규 상장, 고점 대비 하락률, 최근 변동성, CCI 지표 등을 기준으로 필터링합니다.
2.  **`binance_futures_screener.py`**: 바이낸스 선물 시장의 데이터를 분석하여 특정 조건을 만족하는 코인을 찾습니다. 미결제 약정(OI) 변화, 롱/숏 계정 비율, 펀딩비 등을 주요 지표로 사용합니다.
3.  **`daily_screener.py`**: 매일 실행하여 업비트(Upbit) 원화(KRW) 마켓의 모든 코인을 분석하고, 설정된 기준(차트 패턴, 거래량 분석)에 맞는 '관심 코인'을 선정합니다. 선정된 코인은 `watchlist.txt` 파일에 요약되고, 상세 차트 이미지는 `charts/` 폴더에 저장됩니다.

## 시스템 아키텍처

```mermaid
graph TD
    subgraph 사용자
        A[실행] --> B{스크리너 선택};
    end

    subgraph 스크리너
        B --> C[altcoin_screener.py];
        B --> D[binance_futures_screener.py];
        B --> E[daily_screener.py];
    end

    subgraph 데이터 소스
        F[Upbit API]
        G[Binance API]
    end

    subgraph 데이터 처리
        H[ccxt 라이브러리]
        I[python-binance 라이브러리]
        J[pandas / pandas-ta]
    end

    subgraph 결과물
        K[watchlist.txt]
        L[charts/ 폴더 (이미지)]
        M[콘솔 출력]
    end

    C --> H;
    D --> I;
    E --> H;

    H --> F;
    I --> G;

    H --> J;
    I --> J;

    J --> C;
    J --> D;
    J --> E;

    C --> M;
    D --> M;
    E --> K;
    E --> L;
    E --> M;
```

## 주요 기능 및 설정

### `altcoin_screener.py`

-   **목적**: 특정 패턴(MOVE/KRW, IMX/KRW 유사)을 가진 알트코인 탐색
-   **주요 설정값**:
    -   `MAX_LISTING_DAYS`: 최대 상장일
    -   `MIN_DOWNTREND_FROM_ATH`: 고점 대비 최소 하락률
    -   `MIN_VOLATILITY`, `MAX_VOLATILITY`: 최근 변동성 범위
    -   `MIN_CCI`, `MAX_CCI`: CCI 지표 범위
-   **선택적 필터**: RSI, 거래량 증가율 필터를 활성화/비활성화할 수 있습니다.

### `binance_futures_screener.py`

-   **목적**: 바이낸스 선물 시장에서 특정 조건을 만족하는 코인 탐색
-   **주요 설정값**:
    -   `OI_CHANGE_24H_MIN`, `OI_CHANGE_4H_MIN`: 미결제 약정 최소 변화율
    -   `LONG_ACCOUNTS_1H_MIN`, `LONG_ACCOUNTS_1H_MAX`: 롱 포지션 계정 비율 범위
    -   `PRICE_CHANGE_24H_MAX`: 최대 가격 변화율
    -   `OI_VOLUME_24H_MIN`: 거래량 대비 미결제 약정 비율
    -   `FUNDING_RATE_AVG_MIN`: 평균 펀딩비

### `daily_screener.py`

-   **목적**: 매일 업비트 원화 마켓을 분석하여 관심 코인 선정 및 리포트 생성
-   **주요 설정값**:
    -   `MIN_DAILY_VOLUME_KRW`: 최소 일일 거래대금
    -   `MIN_DOWNTREND_FROM_ATH`: 고점 대비 최소 하락률
    -   `MIN_VOLATILITY_30D`, `MAX_VOLATILITY_30D`: 30일 변동성 범위
    -   `MIN_CCI`, `MAX_CCI`: CCI 지표 범위
-   **결과물**:
    -   `watchlist.txt`: 분석 결과 요약 텍스트 파일
    -   `charts/`: 선정된 코인의 상세 차트 이미지 파일

## 설치 및 실행 방법

1.  **가상환경 설정 및 의존성 설치**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **스크리너 실행**:
    -   알트코인 스크리너 실행:
        ```bash
        python altcoin_screener.py
        ```
    -   바이낸스 선물 스크리너 실행:
        ```bash
        python binance_futures_screener.py
        ```
    -   데일리 스크리너 실행:
        ```bash
        python daily_screener.py
        ```

## 참고

-   이 프로젝트는 투자 추천이 아니며, 모든 투자의 책임은 본인에게 있습니다.
-   API 사용 시 각 거래소의 정책 및 속도 제한(Rate Limit)을 준수해야 합니다.
