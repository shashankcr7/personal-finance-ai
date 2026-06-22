import psycopg2
import pytest

import config
import db

TEST_USER_EMAIL = "test-fixture@personal-finance-ai.local"


def _ensure_test_user() -> str:
    supabase = db.get_supabase()

    for user in supabase.auth.admin.list_users():
        if user.email == TEST_USER_EMAIL:
            user_id = user.id
            break
    else:
        created = supabase.auth.admin.create_user(
            {
                "email": TEST_USER_EMAIL,
                "password": "test-fixture-password-unused",
                "email_confirm": True,
            }
        )
        user_id = created.user.id

    connection = psycopg2.connect(config.DATABASE_URL)
    try:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO public.users (id, email) VALUES (%s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (user_id, TEST_USER_EMAIL),
            )
        connection.commit()
    finally:
        connection.close()

    return user_id


@pytest.fixture(scope="session")
def test_user_id() -> str:
    return _ensure_test_user()


@pytest.fixture
def conn():
    connection = psycopg2.connect(config.DATABASE_URL)
    yield connection
    connection.rollback()
    connection.close()
