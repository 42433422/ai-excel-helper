from unittest.mock import Mock, patch


def test_shipment_generate_then_print_document(client):
    # 语音/ASR 场景：把“酒吧零三”纠正为 9803
    order_text = "帮我打印一下发货单。七彩乐园的一桶酒吧零三的规格28"

    shipment_service = Mock()
    shipment_service.generate_shipment_document.return_value = {
        "success": True,
        "document_path": "C:/mock/shipment_9803.pdf",
        "message": "mock generated",
    }

    with patch("app.bootstrap.get_shipment_service", return_value=shipment_service):
        resp = client.post(
            "/api/tools/execute",
            json={
                "tool_id": "shipment_generate",
                "action": "run",
                "params": {"order_text": order_text},
            },
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    # 断言解析是否把关键字段归一化到了预期值
    _, kwargs = shipment_service.generate_shipment_document.call_args
    assert kwargs["unit_name"] == "七彩乐园"
    assert kwargs["products"][0]["quantity_tins"] == 1
    assert kwargs["products"][0]["model_number"] == "9803"
    assert float(kwargs["products"][0]["tin_spec"]) == 28

    # 接着走打印接口（这里用 stub，避免真实文件/打印机依赖）
    printer_service = Mock()
    printer_service.print_document.return_value = {
        "success": True,
        "message": "mock printed",
        "printer": "mock_printer",
    }

    with patch("app.routes.print.get_printer_service", return_value=printer_service), patch(
        "app.routes.print.os.path.exists", return_value=True
    ):
        resp2 = client.post(
            "/api/print/document",
            json={"file_path": data["document_path"]},
            content_type="application/json",
        )

    assert resp2.status_code == 200
    assert resp2.get_json()["success"] is True
    printer_service.print_document.assert_called()

