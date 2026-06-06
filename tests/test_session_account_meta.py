from app.application.session_account_meta import validate_account_kind_for_market


def test_admin入口必须是市场管理员账号():
    assert (
        validate_account_kind_for_market(
            "admin",
            is_enterprise=True,
            is_market_admin=False,
        )
        is not None
    )
    assert (
        validate_account_kind_for_market(
            "admin",
            is_enterprise=False,
            is_market_admin=True,
        )
        is None
    )


def test_企业入口只允许非管理员企业账号():
    assert (
        validate_account_kind_for_market(
            "enterprise",
            is_enterprise=True,
            is_market_admin=False,
        )
        is None
    )

    admin_err = validate_account_kind_for_market(
        "enterprise",
        is_enterprise=True,
        is_market_admin=True,
    )
    assert admin_err is not None
    assert "管理员入口" in admin_err

    normal_err = validate_account_kind_for_market(
        "enterprise",
        is_enterprise=False,
        is_market_admin=False,
    )
    assert normal_err is not None
    assert "企业版账号" in normal_err
