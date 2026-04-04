---
name: "label-template-generator"
description: "Generates Python label template code from reference images with OCR. Invoke when user wants to create labels from images, extract fixed labels and variable data, or convert label images to code."
---

# Label Template Generator

This skill enables AI to analyze label images and generate corresponding Python code templates that can be used to recreate similar labels programmatically using Pillow (PIL).

## When to Use This Skill

Invoke this skill when:
- User asks to create a new label template based on an image
- User wants to convert an existing label image to Python code
- User needs to identify fixed labels vs variable data in a label
- User wants to generate label templates programmatically
- User asks "how to create this label" or "turn this image into code"
- User needs to extract field structure from product labels

## Features

### 1. Image Analysis
- Extract image dimensions, format, and colors
- Detect background and border colors
- Estimate layout sections

### 2. OCR Text Extraction (Optional)
- Extract text from label images using **PaddleOCR** (`extract_text_with_ocr` in the Python module), plus OpenCV-based grid line detection for label/value pairing
- Identify fixed labels (e.g., "品名:", "颜色:", "货号:")
- Extract variable data values (e.g., "XX 运动鞋", "白色", "1635")
- Recognize common label field patterns
- **Note:** Label images now use the same `OCRService` as `/api/ocr` (PaddleOCR first, then EasyOCR/Tesseract). See `app/services/skills/label_template_generator/RECOGNITION_TEMPLATE_OCR.md`.

### 3. Barcode Generation (NEW!)
- **Automatic barcode generation** from label data
- Support multiple barcode formats: EAN-13, Code128, Code39
- Auto-compose barcode data from item_number + code_segment
- Custom barcode data support
- Centered barcode placement on label

### 4. Code Generation
- Generate complete Python label generator classes
- Support for both OCR-enabled and basic modes
- Automatically define field structure with editable flags
- Include example usage and field template methods
- **Integrated barcode generation code**

## How to Use

### Python Module

```python
from app.services.skills.label_template_generator.label_template_generator import (
    LabelTemplateGeneratorSkill,
)

skill = LabelTemplateGeneratorSkill()

# Generate template with OCR
result = skill.execute(
    image_path="path/to/label.png",
    class_name="MyLabelGenerator",
    output_file="my_label_generator.py",
    enable_ocr=True,
    verbose=True
)

if result['success']:
    print(f"Generated code: {len(result['code'])} characters")
    
    # View extracted fields
    if result.get('ocr_result') and result['ocr_result'].get('fields'):
        for field in result['ocr_result']['fields']:
            print(f"  {field['label']}: {field['value']} (type: {field['type']})")
```

### Command Line

```bash
# With OCR (recommended)
python label_template_generator.py -i input.png -o output.py -n MyLabelGenerator

# Without OCR
python label_template_generator.py -i input.png -o output.py -n MyLabelGenerator --no-ocr

# Verbose mode
python label_template_generator.py -i input.png -v
```

Options:
- `-i, --image`: Input image path (required)
- `-o, --output`: Output Python file path
- `-n, --name`: Class name for the generated template
- `--no-ocr`: Disable OCR recognition
- `-v, --verbose`: Verbose output mode

## Output Format

### With OCR Enabled

The generator returns Python code with:
- Field definitions with labels and default values
- Type information (fixed_label vs dynamic)
- Editable flags for each field
- Example data structure

Example extracted fields:
```python
self.fields = {
    "product_name": {
        "label": "品名",
        "default_value": "XX 运动鞋",
        "type": "fixed_label",
        "editable": True
    },
    "color": {
        "label": "颜色",
        "default_value": "白色",
        "type": "fixed_label",
        "editable": True
    },
    "item_number": {
        "label": "货号",
        "default_value": "1635",
        "type": "fixed_label",
        "editable": True
    }
}
```

### Usage Example

```python
generator = ShoeLabelGenerator(output_dir="./labels")

# Data dictionary - variable values can be changed
data = {
    "product_name": "XX 运动鞋",
    "color": "白色",
    "item_number": "1635",
    "code_segment": "00001",
    "grade": "合格品",
    "standard": "QB/T4331-2013",
    "price": "199",
    # Barcode options:
    "auto_barcode": True  # Auto-generate from item_number + code_segment
    # OR use custom barcode data:
    # "barcode_data": "163500001"
}

# Generate label with barcode
filename = generator.generate_label(data, "ORDER-001", 1)

# Get field template to see structure
template = generator.get_field_template()
for key, info in template.items():
    print(f"{key}: {info}")
```

### Barcode Data Options

The generated code supports multiple ways to provide barcode data:

1. **Auto-generate** (Recommended):
   ```python
   data = {
       "item_number": "1635",
       "code_segment": "00001",
       "auto_barcode": True  # Generates "163500001"
   }
   ```

2. **Custom barcode data**:
   ```python
   data = {
       "barcode_data": "163500001",  # Direct barcode value
       "barcode_type": "code128"     # Optional: specify type
   }
   ```

3. **EAN-13 barcode** (for retail products):
   ```python
   data = {
       "barcode_data": "123456789012",  # 12 digits for EAN-13
       "auto_barcode": False
   }
   ```

The generated code will automatically:
- Choose appropriate barcode type (EAN-13 for 12+ digit numbers, Code128 otherwise)
- Center the barcode on the label
- Display human-readable text below the barcode
- Fall back to a placeholder if barcode library is not installed

## Dependencies

### Required
- Pillow (PIL) for image handling: `pip install Pillow`

### Optional (for OCR on label images)
- **PaddleOCR** (what the implementation uses): `pip install paddlepaddle paddleocr` (see Paddle docs for GPU/CUDA)
- OpenCV (`opencv-python`) and NumPy are required by `extract_text_with_ocr` for grid detection

### Optional (for Barcode Generation)
- python-barcode: `pip install python-barcode`
  - Provides barcode generation for EAN-13, Code128, Code39, etc.
  - Falls back to placeholder if not installed

## Common Label Patterns

The skill recognizes these common Chinese label patterns:
- 品名 / 产品名称 → product_name
- 颜色 → color
- 货号 / 产品编号 → item_number
- 码段 → code_segment
- 等级 → grade
- 执行标准 → standard
- 统一零售价 / 价格 → price

## Example Output

For a shoe label image, the generated code will:
1. Define all fields with their labels and example values
2. Provide a `generate_label()` method that accepts a data dictionary
3. Include a `get_field_template()` method to show field structure
4. Draw each field at appropriate positions

## Notes

- Without OCR, the skill uses a fallback pattern-based approach
- OCR accuracy depends on image quality and font clarity
- Generated code can be customized to adjust layout and styling
- The skill supports PNG, JPG, and other common image formats
