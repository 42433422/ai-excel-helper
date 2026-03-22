from app.services.wechat_contact_service import WechatContactService


def main() -> None:
    s = WechatContactService()
    keyword = "骗子"
    r1 = s._search_contacts_from_wechat_db(keyword=keyword, limit=20)
    r2 = s.get_contacts(keyword=keyword, contact_type=None, starred_only=False, limit=20)
    print("keyword", keyword)
    print("fallback_contact_db_count", len(r1))
    if r1:
        print("fallback_first_5", r1[:5])
    print("get_contacts_count", len(r2))
    if r2:
        print("get_contacts_first_5", r2[:5])


if __name__ == "__main__":
    main()

