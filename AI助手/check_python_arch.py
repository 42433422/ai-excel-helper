import struct
import sys

print(f"Python版本: {sys.version}")
print(f"Python架构: {struct.calcsize('P') * 8}-bit")
print(f"平台: {sys.platform}")
