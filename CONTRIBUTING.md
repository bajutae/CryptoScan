# 기여 가이드라인

이 프로젝트에 기여해 주셔서 감사합니다! 여러분의 기여는 이 프로젝트를 더욱 발전시키는 데 큰 도움이 됩니다.

## 코드 오브 컨덕트 (Code of Conduct)

이 프로젝트는 모든 기여자가 환영받고 안전한 환경에서 참여할 수 있도록 [행동 강령](CODE_OF_CONDUCT.md)을 준수합니다. 모든 상호 작용에서 존중과 포용을 실천해 주시기 바랍니다.

## 이슈 보고

버그를 발견했거나 새로운 기능을 제안하고 싶다면, 먼저 [이슈](https://github.com/your-username/your-repo-name/issues)를 검색하여 이미 보고된 내용이 있는지 확인해 주세요. 만약 없다면, 새로운 이슈를 생성하고 다음 정보를 포함해 주세요:

*   **버그 보고:**
    *   버그를 재현하는 단계
    *   예상되는 동작
    *   실제 동작
    *   스크린샷 또는 오류 메시지 (가능한 경우)
    *   운영 체제 및 Python 버전
*   **기능 제안:**
    *   제안하는 기능에 대한 명확하고 간결한 설명
    *   이 기능이 해결할 문제 또는 제공할 이점
    *   가능한 경우, 사용 사례 예시

## 코드 기여

코드 기여는 다음 단계를 따릅니다.

1.  **프로젝트 포크 및 클론:**
    ```bash
    git clone https://github.com/[your-username]/[your-repo-name].git
    cd your-repo-name
    ```

2.  **새 브랜치 생성:**
    작업할 내용에 따라 의미 있는 이름으로 브랜치를 생성합니다. (예: `feature/new-screener`, `bugfix/fix-daily-chart`)
    ```bash
    git checkout -b your-feature-branch-name
    ```

3.  **코드 변경:**
    원하는 변경 사항을 구현합니다.

4.  **코드 스타일 준수:**
    이 프로젝트는 [Black](https://github.com/psf/black)과 [Flake8](https://flake8.pycqa.org/en/latest/)을 사용하여 코드 스타일을 관리합니다. 커밋하기 전에 다음 명령어를 실행하여 코드 스타일을 확인하고 자동으로 포맷팅해 주세요.
    ```bash
    black .
    flake8 .
    ```

5.  **테스트 작성 및 실행:**
    새로운 기능을 추가하거나 버그를 수정하는 경우, 관련 테스트 코드를 작성하거나 기존 테스트를 업데이트해야 합니다. 모든 테스트가 통과하는지 확인하세요.
    ```bash
    python -m unittest discover tests
    ```

6.  **커밋 메시지 작성:**
    커밋 메시지는 변경 사항을 명확하고 간결하게 설명해야 합니다. 다음 가이드라인을 따르는 것을 권장합니다.
    *   첫 줄은 50자 이내로 요약합니다.
    *   두 번째 줄은 비워둡니다.
    *   세 번째 줄부터는 변경 사항에 대한 자세한 설명을 작성합니다.
    *   관련 이슈가 있다면 `Fixes #이슈번호` 또는 `Closes #이슈번호`와 같이 참조합니다.

    ```
    feat: Add new altcoin screening criteria

    This commit introduces new criteria for altcoin screening, including
    volume spike detection and recent price volatility. This helps to
    identify more potential altcoins for analysis.

    Closes #123
    ```

7.  **풀 리퀘스트 (Pull Request) 제출:**
    변경 사항을 `main` 브랜치로 풀 리퀘스트를 제출합니다. 풀 리퀘스트 설명에는 다음 내용을 포함해 주세요:
    *   무엇을 변경했는지
    *   왜 변경했는지
    *   어떻게 테스트했는지
    *   관련 이슈 번호

    리뷰어의 피드백에 열린 마음으로 임해 주세요.

## 질문

궁금한 점이 있다면 언제든지 이슈를 통해 질문해 주세요.