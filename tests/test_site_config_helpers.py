import pytest

from onesite.config import SiteConfig, Timezone, postgres_url


def test_timezone_enum_serializes_to_its_iana_name():
    config = SiteConfig(extra={"TIMEZONE": Timezone.AMERICA_NEW_YORK})

    assert config.model_dump(mode="json")["extra"]["TIMEZONE"] == "America/New_York"


def test_postgres_url_encodes_connection_components_and_query_params():
    assert postgres_url(
        host="db.example.com",
        port=5433,
        user="app user",
        password="p@ss/word",
        db="app/database",
        params={"sslmode": "require", "application_name": "One Site"},
    ) == (
        "postgresql://app%20user:p%40ss%2Fword@db.example.com:5433/"
        "app%2Fdatabase?sslmode=require&application_name=One+Site"
    )


def test_postgres_url_supports_ipv6_and_optional_password():
    assert postgres_url(host="::1", password=None) == "postgresql://postgres@[::1]:5432/app"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"host": ""}, "host"),
        ({"port": 0}, "port"),
        ({"user": ""}, "user"),
        ({"db": ""}, "database"),
    ],
)
def test_postgres_url_rejects_invalid_required_components(kwargs, message):
    with pytest.raises(ValueError, match=message):
        postgres_url(**kwargs)
