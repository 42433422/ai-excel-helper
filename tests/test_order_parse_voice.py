import pytest


def test_parse_order_text_voice_shipment_generate():
    from app.routes.tools import _parse_order_text

    text = "七彩乐园的一桶酒吧零三的规格28"
    result = _parse_order_text(text)

    assert result["success"] is True
    assert result["unit_name"] == "七彩乐园"
    assert len(result["products"]) == 1

    product = result["products"][0]
    assert product["quantity_tins"] == 1
    assert product["model_number"] == "9803"
    # tin_spec 可能是 float
    assert float(product["tin_spec"]) == 28


def test_intent_recognition_shipment_generate_from_voice_style():
    from app.services.intent_service import recognize_intents

    text = "七彩乐园的一桶酒吧零三的规格28"
    result = recognize_intents(text)

    # 依赖后续 shipment_generate 兜底逻辑；此测试会在 intent_service 修复后通过
    assert result["tool_key"] == "shipment_generate"
    assert result["primary_intent"] == "shipment_generate"


def test_parse_order_text_missing_bucket_should_ask():
    from app.routes.tools import _parse_order_text

    text = "打印一下七彩乐园的9803规格28"
    result = _parse_order_text(text)

    assert result["success"] is False
    assert "需要多少桶" in result["message"]


def test_intent_recognition_print_model_spec_missing_bucket():
    from app.services.intent_service import recognize_intents

    text = "打印一下七彩乐园的9803规格28"
    result = recognize_intents(text)

    assert result["tool_key"] == "shipment_generate"
    assert result["primary_intent"] == "shipment_generate"


def test_parse_order_text_colloquial_any_order():
    from app.routes.tools import _parse_order_text

    text = "哎，给我打印一下七彩乐园的发货单，嗯，编号9803，规格二十八一共三桶。"
    result = _parse_order_text(text)

    assert result["success"] is True
    assert result["unit_name"] == "七彩乐园"
    product = result["products"][0]
    assert product["model_number"] == "9803"
    assert product["quantity_tins"] == 3
    assert float(product["tin_spec"]) == 28


def test_parse_order_text_missing_spec_should_ask():
    from app.routes.tools import _parse_order_text

    text = "打印一下七彩乐园发货单，编号9803，一共三桶"
    result = _parse_order_text(text)

    assert result["success"] is False
    assert "还缺少规格" in result["message"]


def test_intent_recognition_colloquial_should_prefer_shipment():
    from app.services.intent_service import recognize_intents

    text = "给我打印七彩乐园发货单，编号9803，规格二十八，一共三桶"
    result = recognize_intents(text)

    assert result["tool_key"] == "shipment_generate"


@pytest.mark.parametrize(
    "text",
    [
        "发货单七彩乐园9803规格12要3桶",
        "发货单七彩乐园9803规格12来3桶",
    ],
)
def test_parse_order_text_colloquial_qty_verbs_should_succeed(text):
    from app.routes.tools import _parse_order_text

    result = _parse_order_text(text)

    assert result["success"] is True
    assert result["unit_name"] == "七彩乐园"
    assert len(result["products"]) == 1
    product = result["products"][0]
    assert product["model_number"] == "9803"
    assert product["quantity_tins"] == 3
    assert float(product["tin_spec"]) == 12

