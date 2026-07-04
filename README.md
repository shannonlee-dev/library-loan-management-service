# 코드 도서관

FastAPI, SQLAlchemy, Jinja2로 만든 세션 기반 SSR 도서 대여 서비스입니다. 이전 도서 기록장 앱을 확장해 사용자 인증, 보호 경로, 관계형 대여 기록, 상태 변경 흐름을 통합했습니다.

## GitHub 저장소 링크

- https://github.com/shannonlee-dev/sandbox

## 실행 환경

- Python: 3.10 이상
- FastAPI: 0.110 이상
- Uvicorn: 0.29 이상
- SQLAlchemy: 2.0 이상
- Jinja2: 3.1 이상
- python-multipart: 0.0.9 이상
- itsdangerous: 2.1 이상
- DB: SQLite

## 설치와 실행

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

브라우저에서 `http://127.0.0.1:8000/`에 접속합니다.

다른 DB 파일을 사용하려면 실행 전에 `LIBRARY_DATABASE_URL`을 지정합니다. 운영 환경에서는 `SESSION_SECRET_KEY`도 반드시 변경합니다.

```sh
LIBRARY_DATABASE_URL="sqlite:///./local-library.db" SESSION_SECRET_KEY="<CHANGE_ME>" .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

## 테스트 계정

테스트 계정은 애플리케이션 최초 실행 시 DB의 `users` 테이블에 해시 비밀번호로 저장됩니다.

| ID | PW | 표시 이름 |
|---|---|---|
| `demo` | `demo1234` | 데모 사용자 |

회원가입 화면에서 새 계정을 만들 수도 있으며, 비밀번호는 PBKDF2-HMAC-SHA256 해시로 저장됩니다.

## 인증 방식 선택 사유

Jinja2 SSR 웹 서비스는 브라우저가 페이지 요청마다 쿠키를 자동 전송하므로 세션 방식이 자연스럽습니다. 로그인 성공 시 세션 쿠키에는 사용자 ID만 저장하고, `auth/security.py`의 `Depends` 의존성이 매 요청에서 DB 사용자를 조회합니다. 보호 라우트는 `require_user` 의존성을 선언해 로그인 여부를 확인합니다.

## 공개/보호 경로 정책

| 경로 | 공개 여부 | 설명 |
|---|---|---|
| `/` | 공개 | 서비스 소개와 로그인 상태별 UI |
| `/login` | 공개 | 로그인 화면과 로그인 처리 |
| `/signup` | 공개 | 회원가입 화면과 처리 |
| `/logout` | 로그인 사용자 | 세션 삭제 |
| `/app` | 보호 | 도서 목록, 관계 데이터, 내 대여 기록 |
| `/app/books` | 보호 | 새 도서 등록 |
| `/app/books/{book_id}/borrow` | 보호 | 도서 대여 |
| `/app/loans/{loan_id}/return` | 보호 | 대여중 기록을 반납완료로 변경 |

비로그인 사용자가 `/app` 또는 하위 경로에 접근하면 로그인 화면으로 이동합니다.

## 주요 기능 경로

| 기능 | 경로 |
|---|---|
| 로그인 | `POST /login` |
| 로그아웃 | `POST /logout` |
| 회원가입 | `POST /signup` |
| 도서 검색 | `GET /app?q=<검색어>` |
| 대여 기록 상태 필터 | `GET /app?status=borrowed` 또는 `status=returned` |
| 도서 등록 | `POST /app/books` |
| 도서 대여 | `POST /app/books/{book_id}/borrow` |
| 도서 반납 | `POST /app/loans/{loan_id}/return` |

## ORM 모델과 연관관계

- `User 1:N Loan`: 한 사용자는 여러 대여 기록을 가집니다.
- `Book 1:N Loan`: 한 도서는 시간에 따라 여러 대여 기록을 가집니다.
- `Loan N:1 User`, `Loan N:1 Book`: 대여 기록이 사용자와 도서를 연결하는 중간 모델입니다.

직접 N:M 관계를 매핑하지 않고 `Loan` 모델로 풀었습니다. 대여 상태와 대여·반납 시각이 관계 자체의 중요한 데이터이기 때문입니다. `relationship`과 `back_populates`를 양쪽에 선언했으며, 사용자나 도서가 삭제되면 의미가 사라지는 대여 기록은 `delete-orphan` 정책으로 처리합니다.

## 상태 변경 비즈니스 로직

`services/library_service.py`의 `return_loan`이 핵심 상태 변경을 담당합니다.

1. 요청한 대여 기록이 존재하는지 확인합니다.
2. 로그인 사용자의 대여 기록인지 확인합니다.
3. 현재 상태가 `borrowed`인지 확인합니다.
4. 저장소 계층을 통해 `returned`로 바꾸고 반납 시각을 저장합니다.

대시보드에서 상태가 `대여중`에서 `반납완료`로 바뀌어 결과를 확인할 수 있습니다.

## 전체 서비스 흐름

사용자 관점에서는 로그인 후 보호된 대여 관리 화면에 들어가 도서를 등록하거나 조회하고, 대여 버튼으로 관계 데이터를 생성한 뒤 반납 버튼으로 상태 변경 결과를 확인합니다.

개발자 관점에서는 `routers/`가 HTTP와 SSR 렌더링을, `auth/`가 인증·인가 의존성을, `services/`가 검증과 상태 변경을, `repositories/`가 SQLAlchemy 조회·저장을, `models/`가 관계 매핑을 담당합니다.

## 실패 처리

없는 도서, 이미 대여 중인 도서, 본인이 아닌 대여 기록 반납 같은 실패는 `LibraryError`로 표현하고 `main.py`의 전역 예외 처리기가 일관된 오류 화면을 렌더링합니다.
