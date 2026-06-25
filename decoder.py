import json
from pathlib import Path
from typing import Dict, List
import numpy as np
from PIL import Image
from pathlib import Path



# ---------- 错误类型 ----------
class ErrorKind:
    ImageReadError = "ImageReadError"   
    UnsupportedImageFormat = "UnsupportedImageFormat"
    ImageDecodeError = "ImageDecodeError"


class TranslationError(Exception):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        self.message = message
        super().__init__(f"{kind}: {message}")


# ---------- 常量 ----------
script_dir = Path(__file__).parent      # 代码目录
CLEAN_IMAGE_PATH = script_dir / "data" /"clean_img.png"  # 干净的参考图片路径


# ---------- 简化存档结构（键值对格式） ----------
class ModSaveData:
    """键值对形式的存档数据，方便外部读取和修改"""
    __slots__ = ("slot_id", "ints", "floats", "bools", "vectors", "strings", "magic")

    def __init__(
        self,
        slot_id: int,
        ints: Dict[str, int],
        floats: Dict[str, float],
        bools: Dict[str, bool],
        vectors: Dict[str, List[float]],      # 每个向量的值为 [x, y, z]
        strings: Dict[str, str],
        magic: bytes = b"",
    ):
        self.slot_id = slot_id
        self.ints = ints
        self.floats = floats
        self.bools = bools
        self.vectors = vectors
        self.strings = strings
        self.magic = magic

    def to_dict(self) -> dict:
        """转为可JSON序列化的字典"""
        return {
            "slot_id": self.slot_id,
            "ints": self.ints,
            "floats": self.floats,
            "bools": self.bools,
            "vectors": self.vectors,
            "strings": self.strings,
            "magic": list(self.magic),        # bytes -> int 列表，方便JSON
        }

    def to_json(self, **kwargs) -> str:
        """直接输出JSON字符串"""
        return json.dumps(self.to_dict(), **kwargs)


# ---------- PNG隐写解码 → ModSaveData ----------
def decode_mod_from_png(path: Path) -> ModSaveData:
    """
    从隐写的PNG存档文件中提取数据，返回键值对格式的 ModSaveData。
    """
    # 1. 读取存档图片（去掉Alpha，只保留RGB）
    try:
        save_img = Image.open(path).convert("RGBA")
        save_img = save_img.transpose(Image.FLIP_TOP_BOTTOM)
        save_data = np.array(save_img)[:, :, :3]      # (H, W, 3)
    except Exception as e:
        raise TranslationError(ErrorKind.ImageReadError,
                               f"Failed to open image at {path}: {e}")

    # 2. 读取干净的参考图片
    try:
        clean_img = Image.open(CLEAN_IMAGE_PATH).convert("RGBA")
        clean_img = clean_img.transpose(Image.FLIP_TOP_BOTTOM)
        clean_data = np.array(clean_img)[:, :, :3]
    except Exception as e:
        raise TranslationError(ErrorKind.ImageReadError,
                               f"Failed to open clean image at {CLEAN_IMAGE_PATH}: {e}")

    # 3. 像素差异 → 比特流
    diff = (save_data != clean_data).astype(np.uint8)   # 不同为1，相同为0
    bits = diff.flatten().tolist()                     # 逐像素逐通道展开

    # 4. 比特流 → 字节
    byte_list = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        if len(byte_bits) < 8:
            byte_bits += [0] * (8 - len(byte_bits))    # 不足8位补0
        byte_val = 0
        for j, b in enumerate(byte_bits):
            byte_val |= (b << j)
        byte_list.append(byte_val)

    # 5. 去掉末尾多余的零字节
    while byte_list and byte_list[-1] == 0:
        byte_list.pop()
    data = bytes(byte_list)

    # 6. 分离魔术字节与JSON部分
    json_start = data.find(b"{")
    if json_start == -1:
        raise TranslationError(ErrorKind.ImageDecodeError,
                               "Decoded save data does not contain a JSON object.")
    magic = data[:json_start]
    json_bytes = data[json_start:]

    # 7. 解析JSON
    try:
        json_str = json_bytes.decode("utf-8")
        json_dict = json.loads(json_str)
    except UnicodeDecodeError as e:
        raise TranslationError(ErrorKind.ImageDecodeError,
                               f"Decoded data is not valid UTF-8: {e}")
    except json.JSONDecodeError as e:
        raise TranslationError(ErrorKind.ImageDecodeError,
                               f"Decoded data is not valid JSON: {e}")

    # 8. 映射为 ModSaveData 的键值对结构
    # 游戏原格式中向量存储方式为 {"x":..., "y":..., "z":...} 的列表
    vectors_raw = json_dict.get("vectors", [])
    vector_keys = json_dict.get("vectorKeys", [])
    if len(vector_keys) != len(vectors_raw):
        raise TranslationError(ErrorKind.ImageDecodeError,
                               "Mismatch between vectorKeys and vectors count")
    vectors = {
        k: [v["x"], v["y"], v["z"]]
        for k, v in zip(vector_keys, vectors_raw)
    }

    int_keys = json_dict.get("intKeys", [])
    ints = json_dict.get("ints", [])
    if len(int_keys) != len(ints):
        raise TranslationError(ErrorKind.ImageDecodeError,
                               "Mismatch between intKeys and ints count")
    ints_dict = dict(zip(int_keys, ints))

    float_keys = json_dict.get("floatKeys", [])
    floats = json_dict.get("floats", [])
    if len(float_keys) != len(floats):
        raise TranslationError(ErrorKind.ImageDecodeError,
                               "Mismatch between floatKeys and floats count")
    floats_dict = dict(zip(float_keys, floats))

    bool_keys = json_dict.get("boolKeys", [])
    bools = json_dict.get("bools", [])
    if len(bool_keys) != len(bools):
        raise TranslationError(ErrorKind.ImageDecodeError,
                               "Mismatch between boolKeys and bools count")
    bools_dict = dict(zip(bool_keys, bools))

    string_keys = json_dict.get("stringKeys", [])
    strings = json_dict.get("strings", [])
    if len(string_keys) != len(strings):
        raise TranslationError(ErrorKind.ImageDecodeError,
                               "Mismatch between stringKeys and strings count")
    strings_dict = dict(zip(string_keys, strings))

    return ModSaveData(
        slot_id=json_dict.get("slotID", 0),
        ints=ints_dict,
        floats=floats_dict,
        bools=bools_dict,
        vectors=vectors,
        strings=strings_dict,
        magic=magic,
    )


# ---------- 便捷接口：直接输出JSON ----------
def png_to_json(path: Path, **json_kwargs) -> str:
    """从PNG解码并返回JSON字符串"""
    return decode_mod_from_png(path).to_json(**json_kwargs)

