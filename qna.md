# Basic 6-3 평가 항목별 Q&A

현재 저장소의 구현을 기준으로 정리한 발표·질의응답용 답변입니다. 각 질문에 대한 설명과 확인할 코드를 함께 적었습니다. 관리자 추가와 프론트엔드 분리는 현재 구현이 아닌 확장 방안입니다.

## 항목 1. 기능 구현과 실행

### Q1-1. 사용자가 로그인/로그아웃을 할 수 있고, 성공/실패 여부가 명확히 드러나는가?

**답변:** 아이디와 비밀번호로 로그인하고, 상단 메뉴에서 로그아웃할 수 있습니다.

- 로그인 성공: 비밀번호를 검증한 뒤 기존 세션을 비우고 `user_id`를 저장합니다. `303` 응답으로 `/app`에 이동하며 화면에 “로그인에 성공했습니다.”가 표시됩니다.
- 로그인 실패: `401` 응답과 함께 “아이디 또는 비밀번호가 올바르지 않습니다.”를 로그인 화면에 표시합니다.
- 로그아웃: `POST /logout`에서 세션을 비우고 홈으로 이동하며 “로그아웃되었습니다.”라는 완료 알림을 표시합니다. 상단 메뉴가 사용자 환영 문구·로그아웃에서 로그인·회원가입으로 바뀝니다. 다시 `/app`에 접근하면 로그인 화면으로 이동합니다.

**코드 근거:** [인증 라우터](src/library_service/routers/auth_routes.py), [인증 서비스](src/library_service/services/auth_service.py), [로그인 화면](src/library_service/ui/templates/login.html), [공통 메뉴](src/library_service/ui/templates/base.html), [홈 화면](src/library_service/ui/templates/home.html).

### Q1-2. 비로그인 사용자가 보호 자원에 접근하면 로그인 페이지로 이동하거나 접근 차단 안내가 표시되는가?

**답변:** 보호된 각 라우트에 `Depends(require_user)`를 선언했습니다. 세션에서 유효한 사용자를 찾지 못하면 `LoginRequired` 예외를 발생시킵니다.

브라우저 요청은 전역 예외 처리기가 `303`으로 `/login`에 이동시킵니다. `Accept: application/json` 요청에는 `401`과 “로그인이 필요합니다.”라는 JSON 오류를 반환합니다. 도서 등록·대여·반납 요청에도 같은 검사를 적용하므로 비로그인 사용자는 데이터를 변경할 수 없습니다.

**코드 근거:** [인증 의존성](src/library_service/auth/security.py), [보호 라우터](src/library_service/routers/app_routes.py), [예외 처리](src/library_service/ui/errors.py).

### Q1-3. 비로그인 상태에서 보호된 URL을 브라우저에 직접 입력해도 차단되는가?

**답변:** 네. 비로그인 상태로 주소창에 `/app`을 직접 입력해도 서버가 인증 의존성을 실행해 `/login`으로 이동시킵니다. 메뉴나 버튼을 거치지 않아도 동일한 검사를 받습니다.

도서 등록·대여·반납 경로는 `POST` 전용입니다. 주소창으로 해당 URL을 열면 `GET` 요청이므로 `405 Method Not Allowed`가 됩니다. 해당 경로에 비로그인 상태로 올바른 `POST` 요청을 보내면 인증 검사에서 차단됩니다. 존재하지 않는 `/app` 하위 경로는 `404`로 처리됩니다.

**코드 근거:** [보호 라우터](src/library_service/routers/app_routes.py), [HTTP 검증 테스트](tests/test_http.py)의 `test_public_pages_and_protected_access`, `test_anonymous_users_cannot_mutate_library`.

### Q1-4. 로그인 상태와 비로그인 상태에서 화면 요소가 달라지는가?

**답변:** 네. Jinja2의 `current_user` 조건으로 메뉴와 홈 화면의 이동 버튼을 다르게 렌더링합니다.

| 구분 | 비로그인 | 로그인 |
| --- | --- | --- |
| 상단 메뉴 | 로그인, 회원가입 | 대여 관리, 사용자 환영 문구, 로그아웃 |
| 홈 주요 버튼 | 나의 서재 시작하기 → `/signup` | 서재 둘러보기 → `/app` |
| 대여 관리 화면 | 로그인 필요 | 도서 등록·대여·본인 기록 반납 가능 |

화면 요소를 바꾸는 것은 사용 편의를 위한 처리이고, 실제 접근 권한은 서버의 `require_user`가 검사합니다.

**코드 근거:** [공통 메뉴](src/library_service/ui/templates/base.html), [홈 화면](src/library_service/ui/templates/home.html), [대여 관리 화면](src/library_service/ui/templates/dashboard.html).

### Q1-5. 모델이 최소 3개 이상 존재하고, 연관관계 데이터가 화면에 함께 출력되는가?

**답변:** 네. 핵심 도메인 모델은 `User`, `Book`, `Loan`이며, 소셜 로그인 연결용 `OAuthIdentity`까지 총 4개입니다.

| 모델 | 역할 | 주요 관계 |
| --- | --- | --- |
| `User` | 사용자와 로그인 정보 | 한 사용자의 여러 `Loan` |
| `Book` | 도서 제목·저자·설명 | 한 도서의 여러 `Loan` |
| `Loan` | 사용자와 도서를 연결하는 대여 기록 | 사용자 1명, 도서 1권 |
| `OAuthIdentity` | 외부 인증 제공자와 사용자 연결 | `user_id`로 사용자 참조 |

대시보드는 `book.loans`로 도서의 대여 상태와 누적 기록 수를 구하고, `active[0].user.display_name`으로 현재 대여자를 출력합니다. 내 대여 기록에는 `loan.book.title`과 `loan.book.author`를 함께 출력하므로 여러 모델의 관계를 실제 화면에서 확인할 수 있습니다.

**코드 근거:** [모델](src/library_service/models/entities.py), [대여 관리 화면](src/library_service/ui/templates/dashboard.html), [도서 저장소](src/library_service/repositories/book_repository.py).

### Q1-6. 상태가 변경되는 비즈니스 기능이 있고, 변경 결과를 화면에서 확인할 수 있는가?

**답변:** 네. 도서 대여와 반납이 상태 변경 기능입니다.

1. 대여하면 `status="borrowed"`인 `Loan`을 생성합니다. 화면에서 도서가 “대여중”으로 바뀌고 대여자와 내 대여 기록이 표시됩니다.
2. 본인의 대여 기록을 반납하면 `status`가 `"returned"`로 바뀌고 `returned_at`에 반납 시각을 저장합니다.
3. 화면에 “반납완료”와 반납 시각이 표시되고 해당 기록의 반납 버튼이 사라집니다. 도서는 다시 “대여 가능”으로 표시됩니다.

서비스에서 이미 대여 중인 도서의 중복 대여, 타인의 기록 반납, 이미 반납한 기록의 재반납을 검사합니다. 화면 버튼을 우회해 요청해도 이 규칙을 적용합니다. 다만 현재 중복 대여 검사는 조회 후 생성하는 방식이므로, 동시 요청까지 보장하려면 DB 제약이나 잠금 등 추가 설계가 필요합니다.

**코드 근거:** [대여 서비스](src/library_service/services/library_service.py), [대여 저장소](src/library_service/repositories/loan_repository.py), [대여 관리 화면](src/library_service/ui/templates/dashboard.html).

### Q1-7. README에 실행 방법, 테스트 계정, 공개/보호 경로 정책이 기술되어 있고 절차대로 실행할 수 있는가?

**답변:** [README](README.md)에 Python·uv 요구사항, 설치·실행 명령, 테스트 계정과 공개/보호 경로 정책이 있습니다. 로컬 실행 절차는 다음과 같습니다.

```bash
uv sync --frozen
cp .env.example .env
# .env의 SESSION_SECRET_KEY를 자신만의 값으로 변경합니다.
set -a
. ./.env
set +a
uv run --frozen uvicorn library_service.main:app --host 127.0.0.1 --port 8000
```

접속 주소는 `http://127.0.0.1:8000`입니다. 앱은 `.env`를 자동으로 읽지 않으므로 셸에 환경 변수를 로드해야 합니다. 현재 저장소의 `.python-version`은 Python `3.12`를 지정합니다.

- **로컬 테스트 계정:** `demo` / `demo1234`. 비운영 모드 초기화에서 계정이 없으면 생성합니다. 운영 모드는 데모 계정과 샘플 도서를 생성하지 않으므로 직접 회원가입합니다.
- **공개 화면:** `/`, `/login`, `/signup`. GitHub 인증 시작·콜백 경로와 `/healthz`, 정적 자원도 비로그인 접근이 가능합니다.
- **보호 기능:** `GET /app`, `POST /app/books`, `POST /app/books/{book_id}/borrow`, `POST /app/loans/{loan_id}/return`.
- **로그아웃:** `POST /logout`은 비로그인 상태에서도 호출할 수 있습니다.

실행 확인 시에는 홈 접속 → 비로그인 `/app` 차단 → 데모 로그인 → 대여·반납 → 로그아웃 순서로 확인하면 됩니다. 자동 검증 명령은 `make check`, `make test`입니다.

기존 가상환경이 가리키는 Python `3.12` 실행 파일이 없어, 로그아웃 알림 수정 시에는 별도의 임시 Python `3.13` 환경에서 전체 pytest를 실행했습니다. 로그아웃 알림 표시를 포함한 29개 테스트가 통과했습니다. README 절차에 따른 실제 서버 기동과 브라우저 시연은 별도 확인이 필요합니다.

**코드 근거:** [README](README.md), [환경 변수 예시](.env.example), [초기 데이터 생성](src/library_service/bootstrap.py), [실행 명령](Makefile).

## 항목 2. 계층 분리와 데이터 설계

### Q2-1. 인증, 도메인 로직, 데이터 접근, 화면 처리를 어떤 기준으로 분리했는가?

**답변:** 각 코드가 책임지는 일과 변경되는 이유를 기준으로 나눴습니다.

| 모듈 | 책임 | 예시 |
| --- | --- | --- |
| `auth/` | 요청의 세션 사용자 확인과 로그인 요구, 교차 출처 변경 요청 검사 | `get_optional_user`, `require_user`, `SameOriginMiddleware` |
| `services/` | 인증 검증과 도서 대여의 업무 규칙 | 비밀번호 검증, 중복 대여·소유권·반납 상태 검사 |
| `repositories/` | SQLAlchemy 조회·추가·변경·저장 | 관계 사전 로딩, `commit`, `refresh` |
| `models/` | 테이블과 객체 관계 정의 | `User`, `Book`, `Loan`, `OAuthIdentity` |
| `routers/` | HTTP 입력 수신과 서비스 호출, 렌더링·리다이렉트 선택 | 폼 입력 처리, 대시보드 응답 |
| `ui/` | HTML 템플릿과 공통 오류 응답 | `dashboard.html`, 오류 화면·JSON 선택 |
| `core/`, `bootstrap.py` | DB 연결·요청별 세션 제공과 초기화 | `get_db`, 테이블·데모 데이터 생성 |
| `main.py` | 위 구성 요소를 하나의 앱으로 조립 | 미들웨어·라우터·예외 처리기 등록 |

예를 들어 반납 조건을 바꾸면 서비스를, 조회 최적화를 바꾸면 저장소를, 메뉴를 바꾸면 템플릿을 수정합니다. 업무 규칙을 HTTP 응답 생성과 분리해 서비스 단위로 검증할 수 있습니다.

현재 GitHub OAuth 라우터에는 외부 HTTP 호출과 계정 조회·생성 코드도 들어 있습니다. 일반 인증·대여 흐름은 계층을 분리했지만 OAuth까지 완전히 같은 구조로 나눈 상태는 아닙니다. 확장 시 OAuth 서비스와 저장소로 추출할 수 있습니다.

**코드 근거:** [인증 의존성](src/library_service/auth/security.py), [대여 서비스](src/library_service/services/library_service.py), [대여 저장소](src/library_service/repositories/loan_repository.py), [OAuth 라우터](src/library_service/routers/oauth_routes.py).

### Q2-2. 모델 간 관계를 왜 1:N, N:1로 설계했고, `back_populates`는 어디에 적용했는가?

**답변:** 한 사용자는 여러 번 대여할 수 있고, 한 도서도 반납 후 다시 대여되므로 여러 대여 기록을 가집니다. 각 대여 기록은 사용자 1명과 도서 1권을 가리킵니다.

| 관계 | 양방향 매핑 |
| --- | --- |
| `User 1:N Loan` / `Loan N:1 User` | `User.loans ↔ Loan.user` |
| `Book 1:N Loan` / `Loan N:1 Book` | `Book.loans ↔ Loan.book` |

`User.loans`와 `Book.loans`에는 각각 `back_populates="user"`, `back_populates="book"`을, `Loan.user`와 `Loan.book`에는 `back_populates="loans"`를 선언했습니다. 서로 대응하는 속성을 지정해 같은 관계를 양쪽 객체에서 탐색하고 변경을 동기화합니다.

사용자와 도서의 대여 관계에는 상태·대여 시각·반납 시각이라는 추가 정보가 필요하므로 `Loan`을 독립 모델로 만들었습니다. `Book` 한 행은 이 서비스에서 동시에 한 건만 대여할 수 있는 도서 단위입니다. 여러 복본을 별도 관리하려면 도서 정보와 실물 도서 모델을 추가로 분리해야 합니다.

`OAuthIdentity.user`는 별도의 단방향 관계이며 현재 `back_populates`가 없습니다. 모든 관계를 양방향으로 설정한 것은 아닙니다.

**코드 근거:** [모델](src/library_service/models/entities.py).

### Q2-3. 상태 변경 로직은 어느 계층에 있으며, 왜 그곳에 두었는가?

**답변:** 상태를 바꿀 수 있는지 결정하는 업무 규칙은 `services/library_service.py`에 있습니다. 반납의 경우 `return_loan()`에서 기록 존재 여부, 요청자의 소유권, 현재 `borrowed` 상태를 확인합니다.

검증 후 `repositories/loan_repository.py`의 `mark_returned()`를 호출합니다. 이 함수가 실제로 `status="returned"`, `returned_at=datetime.utcnow()`를 대입하고 DB에 저장합니다.

즉, 서비스는 “어떤 조건에서 변경 가능한가”를 결정하고 저장소는 “변경을 어떻게 저장하는가”를 담당합니다. 라우터는 인증된 사용자와 기록 ID를 전달한 뒤 응답을 만듭니다. 덕분에 향후 JSON API를 추가해도 동일한 업무 규칙을 재사용할 수 있습니다.

현재 트랜잭션 커밋은 저장소 함수에서 수행합니다. 여러 저장소 변경을 하나의 작업으로 묶어야 한다면 서비스나 작업 단위에서 트랜잭션을 관리하도록 조정할 수 있습니다.

**코드 근거:** [대여 서비스의 return_loan](src/library_service/services/library_service.py), [대여 저장소의 mark_returned](src/library_service/repositories/loan_repository.py), [반납 라우트](src/library_service/routers/app_routes.py).

### Q2-4. 부모 모델 삭제 시 자식 데이터 처리 정책은 무엇이며, 왜 선택했는가?

**답변:** `User.loans`와 `Book.loans`에 `cascade="all, delete-orphan"`을 설정했습니다. 사용자를 ORM으로 삭제하면 해당 사용자의 대여 기록을, 도서를 ORM으로 삭제하면 해당 도서의 대여 기록을 함께 삭제합니다. 관계에서 제거되어 고아가 된 대여 객체도 삭제 대상으로 처리합니다.

이 실습에서는 존재하지 않는 사용자나 도서를 참조하는 대여 기록을 남기지 않는 정책을 택했습니다. 사용자 삭제가 도서 삭제로 이어지거나 도서 삭제가 사용자 삭제로 이어지지는 않습니다. 관련 동작은 `test_deleting_user_or_book_removes_orphan_loan_history`에서 검사합니다.

적용 범위에는 두 가지 주의점이 있습니다.

- 현재 설정은 ORM의 cascade이며 외래 키의 DB `ON DELETE CASCADE` 설정은 없습니다. 원시 SQL이나 벌크 삭제가 동일하게 자식 데이터를 정리한다고 가정하면 안 됩니다.
- `OAuthIdentity`에는 같은 삭제 정책을 정의하지 않았습니다. 소셜 로그인 사용자의 삭제를 추가한다면 외부 인증 연결의 정리 정책도 설계해야 합니다. 현재 사용자·도서 삭제용 웹 라우트는 없습니다.

감사·통계 목적으로 대여 이력을 보존해야 하는 실제 서비스라면 삭제 제한이나 소프트 삭제·익명화 등 다른 정책을 검토해야 합니다.

**코드 근거:** [모델의 cascade 설정](src/library_service/models/entities.py), [관계 삭제 테스트](tests/test_library.py).

## 항목 3. 인증과 ORM의 동작 원리

### Q3-1. FastAPI에서 인증/인가가 `Depends`를 통해 어떤 흐름으로 처리되는가?

**답변:** 보호 라우트의 `Depends(require_user)`에서 시작해 필요한 의존성을 순서대로 해결합니다.

```text
요청 쿠키 → SessionMiddleware가 세션 읽기
  → get_db(): 요청에서 사용할 DB 세션 제공
  → get_optional_user(): 세션의 user_id로 DB 사용자 조회
  → require_user(): 사용자 없으면 LoginRequired 발생
  → 인증된 User를 라우트에 전달
  → 서비스에서 업무별 권한 검사 후 처리
```

`get_optional_user`는 사용자가 없어도 `None`을 반환하므로 공개 화면에서 로그인 여부만 확인할 때 사용합니다. `require_user`는 그 결과가 `None`이면 요청 처리를 중단하므로 보호 기능에 사용합니다.

인증은 “누구인가”를 확인하는 과정이고, 인가는 “이 작업을 해도 되는가”를 확인하는 과정입니다. 로그인 여부는 의존성에서 검사하고, “자신의 대여만 반납할 수 있다”는 자원별 권한은 서비스에서 검사합니다. DB 세션은 `get_db()`의 `finally`에서 닫습니다.

**코드 근거:** [인증 의존성](src/library_service/auth/security.py), [DB 의존성](src/library_service/core/database.py), [반납 권한 검사](src/library_service/services/library_service.py).

### Q3-2. 비로그인 사용자의 요청은 왜 차단되며, 어디에서 처리되는가?

**답변:** 보호 기능은 대여자의 신원과 기록 소유권을 알아야 하므로 로그인 사용자를 요구합니다. 세션에 유효한 정수형 `user_id`가 없거나, 해당 ID의 사용자가 DB에 없으면 `get_optional_user()`가 `None`을 반환합니다.

이후 `require_user()`가 `LoginRequired`를 발생시키므로 정상 형식의 비로그인 보호 요청은 라우트 본문과 업무 서비스에 도달하지 않습니다. `main.py`에 등록한 `login_required_handler()`가 브라우저에는 로그인 리다이렉트를, JSON 요청에는 `401` 오류를 반환합니다.

브라우저에서 메뉴를 숨기는 것만으로는 직접 URL 요청을 막을 수 없으므로 서버 의존성에서 검사합니다. 로그인했더라도 다른 사람의 기록을 반납하면 서비스에서 `403`으로 거부합니다.

**코드 근거:** [인증 의존성](src/library_service/auth/security.py), [예외 처리기 등록](src/library_service/main.py), [로그인 필요 응답](src/library_service/ui/errors.py).

### Q3-3. SQLAlchemy 연관관계를 객체 관점에서 어떻게 이해하고, 왜 그렇게 매핑했는가?

**답변:** DB는 외래 키로 행을 연결하고, ORM은 그 연결을 객체의 속성으로 제공합니다. `Loan.user_id`와 `Loan.book_id`는 DB 참조이고, `loan.user`와 `loan.book`은 연결된 객체에 접근하는 통로입니다.

```python
loan.user.display_name  # 이 대여 기록의 사용자 이름
loan.book.title  # 이 대여 기록의 도서 제목
user.loans  # 이 사용자의 대여 기록 목록
book.loans  # 이 도서의 대여 이력 목록
```

이렇게 매핑하면 템플릿과 서비스가 외래 키로 매번 직접 조회하는 대신 업무에서 사용하는 사용자·도서·대여 객체로 데이터를 탐색할 수 있습니다. `back_populates`는 양쪽 속성이 같은 관계를 표현한다는 것을 ORM에 알려 줍니다.

관계 속성을 반복해서 읽으면 추가 쿼리가 많이 발생할 수 있어 저장소에서 `selectinload(Book.loans).selectinload(Loan.user)`처럼 필요한 관계를 사전 로딩합니다. 이는 N+1 조회 문제를 줄이고 화면 렌더링에 필요한 관계 데이터를 준비하기 위한 선택입니다.

**코드 근거:** [모델](src/library_service/models/entities.py), [도서 저장소](src/library_service/repositories/book_repository.py), [사용자 저장소](src/library_service/repositories/user_repository.py), [대여 저장소](src/library_service/repositories/loan_repository.py).

### Q3-4. 단순 CRUD가 아니라 상태 변경 로직이 왜 중요한가?

**답변:** 대여 기록의 값을 수정할 수 있다는 사실만으로는 올바른 대여 업무가 성립하지 않습니다. 누가, 어떤 상태에서, 무엇을 바꿀 수 있는지 제한해야 데이터가 업무 규칙을 지킵니다.

반납은 단순히 문자열을 바꾸는 작업이 아니라 “본인의 대여 중인 기록만 반납할 수 있고, 반납 시각을 함께 기록한다”는 상태 전이입니다. 대여도 이미 대여 중인 도서라면 거부해야 합니다.

따라서 서비스는 `borrowed → returned` 전이를 검증하고, 잘못된 소유권이나 반복 반납을 차단합니다. 테스트에서도 실패 요청 후 기존 상태가 유지되는지 확인합니다. 이런 규칙이 있어야 화면, 향후 API 등 진입 경로가 달라져도 일관된 결과를 얻습니다.

**코드 근거:** [대여 서비스](src/library_service/services/library_service.py), [도메인 테스트](tests/test_library.py), [HTTP 실패 흐름 테스트](tests/test_http.py).

## 항목 4. 전체 구조와 확장 설계

### Q4-1. 전체 구조를 사용자 관점과 개발자 관점에서 설명할 수 있는가?

**답변 — 사용자 관점:** 홈에서 회원가입하거나 로그인합니다. 로그인하면 대여 관리 화면에서 도서를 검색·등록하고 대여할 수 있습니다. 내 대여 기록에서 반납하면 상태와 반납 시각이 표시됩니다. 로그아웃하면 공개 홈으로 돌아가고 대여 관리에는 다시 로그인해야 접근할 수 있습니다.

**답변 — 개발자 관점:** `main.py`가 DB 초기화, 세션 미들웨어, 라우터와 예외 처리기를 연결합니다. 로그인 라우터는 인증 서비스를 통해 계정·비밀번호를 검사하고 세션에 사용자 ID를 저장합니다. 보호 요청에서는 인증 의존성이 DB 사용자를 확인한 뒤 라우터에 전달합니다.

그 뒤 라우터 → 서비스의 업무 검증 → 저장소의 ORM 조회·저장 → DB 순서로 처리합니다. 조회 결과는 Jinja2 템플릿에 전달해 HTML로 반환합니다. 상태 변경 성공 후에는 `303`으로 조회 화면에 이동하는 POST/Redirect/GET 흐름을 사용합니다. 오류는 공통 처리기가 HTML 또는 JSON으로 변환합니다.

**코드 근거:** [앱 구성](src/library_service/main.py), [인증 라우터](src/library_service/routers/auth_routes.py), [대여 라우터](src/library_service/routers/app_routes.py), [대여 서비스](src/library_service/services/library_service.py).

### Q4-2. 양방향 연관관계에서 순환 참조·직렬화 등 어떤 점에 주의해야 하는가?

**답변:** `User.loans → Loan.user → User.loans`처럼 객체를 계속 따라갈 수 있으므로, 관계를 무제한으로 순회하거나 ORM 객체 전체를 재귀적으로 JSON으로 바꾸면 순환 문제가 생길 수 있습니다.

- **응답 범위:** REST API를 만든다면 별도 응답 스키마에 필요한 필드만 정의하고, 중첩 깊이를 제한합니다. 사용자 객체의 `password_hash` 같은 값은 응답에 포함하지 않습니다.
- **조회 비용과 세션:** 관계 접근이 지연 로딩을 일으킬 수 있습니다. 현재처럼 `selectinload`로 필요한 데이터를 준비하고, 세션이 닫힌 뒤 미로딩 관계를 읽지 않도록 합니다.
- **삭제 전파:** 양방향 탐색 관계와 삭제 cascade는 별도 설정입니다. 삭제가 의도치 않게 다른 부모로 퍼지지 않도록 범위를 확인해야 합니다.
- **관계 변경:** `back_populates`가 객체 관계 동기화를 돕더라도 DB 반영에는 flush·commit이 필요합니다. 이를 업무 권한 검사나 동시성 보장으로 해석해서는 안 됩니다.

현재 SSR 템플릿은 `loan.book.title`처럼 필요한 속성만 읽으며 ORM 객체 전체를 JSON으로 직렬화하지 않습니다.

**코드 근거:** [모델](src/library_service/models/entities.py), [관계 사전 로딩](src/library_service/repositories/book_repository.py), [화면의 관계 접근](src/library_service/ui/templates/dashboard.html).

### Q4-3. 관리자 같은 새로운 역할을 추가하려면 무엇을 수정해야 하는가?

**답변:** 현재 `User`에는 역할 필드가 없으며 관리자 기능도 없습니다. 추가한다면 다음 부분을 함께 변경합니다.

1. **모델·DB:** `User.role` 등을 추가하고 기존 사용자를 일반 사용자로 설정하는 마이그레이션을 만듭니다. 현재 `create_all()`만으로 기존 테이블에 새 컬럼이 자동 추가되지는 않습니다.
2. **계정 생성:** 일반 회원가입과 OAuth 신규 계정은 일반 사용자 역할로 생성합니다. 관리자 부여는 별도 승인된 관리 절차로 제한합니다.
3. **인증 의존성:** `require_user`를 재사용하는 `require_admin`을 추가해 로그인하지 않으면 기존 인증 실패 처리를, 일반 사용자이면 `403` 처리를 합니다. 역할은 요청 폼이 아니라 DB 사용자 정보로 판단합니다.
4. **라우터·서비스:** 관리자 기능에 의존성을 적용합니다. 관리자가 타인의 반납을 처리할 수 있는지 등 자원별 업무 정책도 서비스에 명시합니다.
5. **화면·검증:** 관리자 메뉴를 조건부로 출력하고, 일반 사용자의 직접 URL·POST 요청 차단과 역할 변경 적용 여부를 검증합니다.

현재 매 요청마다 사용자 정보를 DB에서 조회하므로 역할도 DB에서 읽으면 변경된 권한을 다음 요청부터 반영할 수 있습니다. 메뉴 표시만 바꾸는 것으로 권한 구현을 끝내면 안 됩니다.

**코드 근거:** [현재 User 모델](src/library_service/models/entities.py), [인증 의존성](src/library_service/auth/security.py), [현재 초기화 방식](src/library_service/bootstrap.py), [공통 메뉴](src/library_service/ui/templates/base.html).

### Q4-4. Jinja2 SSR에서 REST API + 별도 프론트엔드로 전환하면 인증 처리는 어떻게 달라져야 하는가?

**답변:** HTML과 리다이렉트를 중심으로 한 응답을 JSON과 HTTP 상태 코드 중심으로 바꾸고, 프론트엔드가 로그인 화면 이동과 로그인 상태 표시를 담당하게 됩니다. 프론트엔드 분리 자체가 JWT 전환을 반드시 요구하지는 않습니다.

| 선택 | 변경 방향 | 고려할 점 |
| --- | --- | --- |
| 쿠키 세션 유지 | 로그인 API가 쿠키를 설정하고 프론트엔드가 인증 요청에 쿠키를 포함 | 출처가 다르면 credentials와 허용 출처를 명시한 CORS 설정 필요. 사이트 배치에 맞춘 SameSite·Secure 및 CSRF 방어 검토 |
| Bearer 토큰 사용 | 로그인 API가 토큰을 발급하고 프론트엔드가 `Authorization: Bearer ...`로 전달 | 서버의 서명·만료·발급자·대상 검증, 갱신·폐기 정책과 브라우저 저장 위치 설계 필요 |

현재 `require_user`는 세션 쿠키에서 사용자를 찾습니다. 쿠키 방식을 유지하면 이를 재사용할 수 있고, Bearer 방식을 선택하면 토큰에서 신원을 검증하는 의존성을 추가합니다. 대여 소유권 검사는 계속 서비스에 유지합니다.

비로그인 API 요청은 로그인 HTML 리다이렉트 대신 `401` JSON을 반환하고, 로그인했지만 권한이 부족하면 `403`을 반환합니다. 현재도 `Accept: application/json` 인증 오류 처리는 있지만 성공 응답은 SSR이므로 별도 JSON API와 응답 스키마가 필요합니다. 현재 `SameOriginMiddleware`는 다른 출처의 변경 요청을 거부하므로, 별도 출처 프론트엔드를 허용할 때 CORS 설정과 함께 해당 정책도 조정해야 합니다.

**코드 근거:** [현재 인증 의존성](src/library_service/auth/security.py), [JSON 인증 오류 처리](src/library_service/ui/errors.py), [동일 출처 검사](src/library_service/auth/middleware.py), [현재 SSR 라우터](src/library_service/routers/app_routes.py).

### Q4-5. 사용자 수가 증가할 때 현재 인증 방식의 확장성 장단점은 무엇인가?

**답변:** 현재는 Starlette `SessionMiddleware`의 **서명된 쿠키 세션**을 사용합니다. 서버 메모리나 Redis에 세션 데이터를 보관하고 브라우저에는 세션 ID만 주는 방식과 구분해야 합니다. 일반 로그인 후에는 쿠키 세션에 `user_id`를 담고, OAuth 진행 중에는 임시 인증 흐름 정보도 담습니다.

서명은 변조를 검출하기 위한 것이며 암호화가 아닙니다. 쿠키에 비밀번호나 OAuth 액세스 토큰을 저장하지 않습니다. 세션 만료 설정은 12시간이며, `SameSite=Lax`, 운영 모드에서는 `Secure`를 적용합니다.

| 관점 | 현재 서명 쿠키 세션의 특징 |
| --- | --- |
| 서버 증설 | 세션 저장소 동기화가 필요 없고, 인스턴스가 같은 서명 키를 사용하면 쿠키를 검증할 수 있습니다. 사용자 DB도 공유해야 합니다. |
| 처리 비용 | 인증 요청마다 사용자를 DB에서 조회하므로 트래픽 증가 시 DB 연결·조회 비용이 생깁니다. 현재 SQLite 구성은 별도의 확장 검토가 필요합니다. |
| 권한 반영 | 사용자 존재와 향후 DB 역할을 매번 확인하므로 삭제·역할 변경을 요청 단위로 반영할 수 있습니다. |
| 로그아웃·폐기 | 현재 브라우저의 쿠키는 지우지만, 복사된 유효 쿠키를 세션별로 즉시 폐기하는 서버 기능은 없습니다. 서명 키 변경은 모든 기존 세션에 영향을 줍니다. |
| 크기·전송 | 쿠키 크기에 제한이 있고 요청마다 전송되므로 세션 데이터를 작게 유지해야 합니다. |

비교하면 서버 저장형 세션은 Redis 같은 공유 저장소와 조회 비용이 필요하지만 개별 세션 만료·강제 로그아웃을 관리하기 쉽습니다. JWT는 사용자·역할 정보를 토큰에 넣어 DB 조회 없이 검증하도록 설계할 수 있지만, 권한 변경이나 로그아웃을 즉시 반영하려면 짧은 만료·폐기 목록·갱신 토큰 관리 등이 필요합니다. JWT를 쓴다는 사실만으로 확장 문제가 모두 해결되지는 않습니다.

현재 서비스가 커진다면 인증 토큰 형식 변경만 검토하기보다 공유 DB, 연결 관리, 대여 동시성 제어, 세션 폐기 요구사항을 함께 설계해야 합니다.

**코드 근거:** [세션 설정](src/library_service/main.py), [사용자 DB 조회](src/library_service/auth/security.py), [로그인·로그아웃](src/library_service/routers/auth_routes.py), [OAuth 세션 처리](src/library_service/routers/oauth_routes.py), [현재 DB 구성](src/library_service/core/database.py).
