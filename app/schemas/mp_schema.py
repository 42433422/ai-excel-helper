# -*- coding: utf-8 -*-
"""
小程序模块请求/响应 Schema 定义
"""
from marshmallow import Schema, fields, validate, post_load


class WechatLoginSchema(Schema):
    code = fields.Str(required=True, error_messages={"required": "code 不能为空"})


class UserUpdateSchema(Schema):
    display_name = fields.Str(validate=validate.Length(max=64))
    avatar = fields.Url()


class PhoneDecryptSchema(Schema):
    code = fields.Str(required=True)


class CartAddSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(validate=validate.Range(min=1), missing=1)


class CartUpdateSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(validate=validate.Range(min=1))


class AddressCreateSchema(Schema):
    contact_name = fields.Str(required=True, validate=validate.Length(max=32))
    contact_phone = fields.Str(required=True, validate=validate.Length(max=20))
    province = fields.Str(required=True, validate=validate.Length(max=32))
    city = fields.Str(required=True, validate=validate.Length(max=32))
    district = fields.Str(required=True, validate=validate.Length(max=32))
    detail_address = fields.Str(required=True)
    is_default = fields.Bool(missing=False)


class OrderCreateSchema(Schema):
    address_id = fields.Int(required=True)
    remark = fields.Str(missing="")


class FeedbackSubmitSchema(Schema):
    type = fields.Str(required=True, validate=validate.OneOf(
        ["bug", "suggestion", "complaint", "other"]
    ))
    content = fields.Str(required=True, validate=validate.Length(max=1000))
    images = fields.List(fields.Str(), missing=[])


class ProductListSchema(Schema):
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    page_size = fields.Int(missing=20, validate=validate.Range(min=1, max=100))
    keyword = fields.Str(missing="")
    category_id = fields.Int()
    sort_by = fields.Str(
        missing="newest",
        validate=validate.OneOf(["price_asc", "price_desc", "newest", "sales"]),
    )
