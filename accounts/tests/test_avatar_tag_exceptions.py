from __future__ import annotations


class _BadProfile:
    @property
    def avatar(self):  # pragma: no cover - we want exception in tag
        raise RuntimeError("boom")


class _User:
    is_authenticated = True
    pk = 123
    profile = _BadProfile()


def test_avatar_url_handles_profile_errors():
    from accounts.templatetags.avatar import avatar_url

    # When profile/avatar access raises, tag returns empty string
    assert avatar_url(_User(), size=64) == ""


class _GoodAvatar:
    url = "/media/avatars/example.png"


class _GoodProfile:
    avatar = _GoodAvatar()


class _UserWithAvatar:
    profile = _GoodProfile()


def test_avatar_url_prefers_uploaded_avatar():
    from accounts.templatetags.avatar import avatar_url

    assert avatar_url(_UserWithAvatar(), size=32) == "/media/avatars/example.png"
