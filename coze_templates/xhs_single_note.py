"""
小红书单条笔记采集 - Coze 代码节点版本
适用于 Coze 工作流的代码节点

输入参数:
- bijilianjie: 笔记链接
- cookie: 小红书 Cookie

输出:
- records: 飞书多维表格记录数组
"""

import re
import json
import time
import hashlib
import random
import secrets
import base64
import struct
import urllib.parse
from typing import Dict, Any, Optional
from http.cookies import SimpleCookie
import requests


# ==================== 签名生成相关类 ====================

DEBUG_ENABLED = False


def _set_debug(enabled):
    global DEBUG_ENABLED
    DEBUG_ENABLED = bool(enabled)


def _boolish(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "y", "on")


def _mask(value, keep=4):
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if len(text) <= keep * 2:
        return "*" * len(text)
    return text[:keep] + "*" * (len(text) - keep * 2) + text[-keep:]


def _debug(message):
    if DEBUG_ENABLED:
        print(message)


def _debug_kv(label, value, mask=False):
    if not DEBUG_ENABLED:
        return
    show_value = _mask(value) if mask else value
    print(f"[debug] {label}: {show_value}")

class RC4:
    """RC4 加密"""
    def __init__(self, key_bytes):
        self._key = key_bytes

    def encrypt(self, plaintext):
        key = self._key
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + key[i % len(key)]) % 256
            s[i], s[j] = s[j], s[i]

        i = 0
        j = 0
        out = bytearray()
        for byte in plaintext:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            k = s[(s[i] + s[j]) % 256]
            out.append(byte ^ k)
        return bytes(out)


class FPData:
    """浏览器指纹数据"""
    GPU_VENDORS = [
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 520 (0x1912) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00003EA0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB (0x000010DE) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x0000250F) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 580 2048SP (0x00006FDF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ]

    SCREEN_RESOLUTIONS = {
        "resolutions": ["1366;768", "1600;900", "1920;1080", "2560;1440"],
        "weights": [0.25, 0.15, 0.45, 0.15],
    }

    COLOR_DEPTH_OPTIONS = {"values": [24, 32], "weights": [0.7, 0.3]}
    DEVICE_MEMORY_OPTIONS = {"values": [4, 8, 16], "weights": [0.4, 0.4, 0.2]}
    CORE_OPTIONS = {"values": [4, 6, 8], "weights": [0.5, 0.3, 0.2]}

    BROWSER_PLUGINS = "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF"
    CANVAS_HASH = "742cc32c"
    VOICE_HASH_OPTIONS = "10311144241322244122"
    FONTS = 'system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif'


def weighted_random_choice(options, weights):
    return f"{random.choices(options, weights=weights, k=1)[0]}"


def get_renderer_info():
    renderer_str = random.choice(FPData.GPU_VENDORS)
    vendor, renderer = renderer_str.split("|")
    return vendor, renderer


def get_screen_config():
    width_str, height_str = weighted_random_choice(
        FPData.SCREEN_RESOLUTIONS["resolutions"],
        FPData.SCREEN_RESOLUTIONS["weights"],
    ).split(";")
    width = int(width_str)
    height = int(height_str)
    avail_width = width - random.choice([0, 30, 60])
    avail_height = height - random.choice([30, 60, 80])
    return {"width": width, "height": height, "availWidth": avail_width, "availHeight": avail_height}


class CryptoConfig:
    """加密配置"""
    def __init__(self):
        self.MAX_32BIT = 0xFFFFFFFF
        self.MAX_SIGNED_32BIT = 0x7FFFFFFF
        self.MAX_BYTE = 255

        self.STANDARD_BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        self.CUSTOM_BASE64_ALPHABET = "ZmserbBoHQtNP+wOcza/LpngG8yJq42KWYj0DSfdikx3VT16IlUAFM97hECvuRX5"
        self.X3_BASE64_ALPHABET = "MfgqrsbcyzPQRStuvC7mn501HIJBo2DEFTKdeNOwxWXYZap89+/A4UVLhijkl63G"

        self.HEX_KEY = (
            "71a302257793271ddd273bcee3e4b98d9d7935e1da33f5765e2ea8afb6dc77a5"
            "1a499d23b67c20660025860cbf13d4540d92497f58686c574e508f46e1956344"
            "f39139bf4faf22a3eef120b79258145b2feb5193b6478669961298e79bedca64"
            "6e1a693a926154a5a7a1bd1cf0dedb742f917a747a1e388b234f2277"
        )

        self.VERSION_BYTES = [119, 104, 96, 41]
        self.SEQUENCE_VALUE_MIN = 15
        self.SEQUENCE_VALUE_MAX = 50
        self.WINDOW_PROPS_LENGTH_MIN = 900
        self.WINDOW_PROPS_LENGTH_MAX = 1200

        self.CHECKSUM_VERSION = 1
        self.CHECKSUM_XOR_KEY = 115
        self.CHECKSUM_FIXED_TAIL = [249, 65, 103, 103, 201, 181, 131, 99, 94, 7, 68, 250, 132, 21]

        self.ENV_FINGERPRINT_XOR_KEY = 41
        self.ENV_FINGERPRINT_TIME_OFFSET_MIN = 10
        self.ENV_FINGERPRINT_TIME_OFFSET_MAX = 50

        self.SIGNATURE_DATA_TEMPLATE = {"x0": "4.2.6", "x1": "xhs-pc-web", "x2": "Windows", "x3": "", "x4": ""}
        self.X3_PREFIX = "mns0301_"
        self.XYS_PREFIX = "XYS_"

        self.B1_SECRET_KEY = "xhswebmplfbt"
        self.SIGNATURE_XSCOMMON_TEMPLATE = {
            "s0": 5, "s1": "", "x0": "1", "x1": "4.2.6", "x2": "Windows",
            "x3": "xhs-pc-web", "x4": "4.86.0", "x5": "", "x6": "", "x7": "",
            "x8": "", "x9": -596800761, "x10": 0, "x11": "normal",
        }

        self.PUBLIC_USERAGENT = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
        )


class BitOperations:
    def __init__(self, config):
        self.config = config

    def xor_transform_array(self, source_integers):
        result_bytes = bytearray(len(source_integers))
        key_bytes = bytes.fromhex(self.config.HEX_KEY)
        key_length = len(key_bytes)
        for index in range(len(source_integers)):
            if index < key_length:
                result_bytes[index] = (source_integers[index] ^ key_bytes[index]) & 0xFF
            else:
                result_bytes[index] = source_integers[index] & 0xFF
        return result_bytes


class Base64Encoder:
    def __init__(self, config):
        self.config = config
        self._custom_encode_table = str.maketrans(config.STANDARD_BASE64_ALPHABET, config.CUSTOM_BASE64_ALPHABET)
        self._x3_encode_table = str.maketrans(config.STANDARD_BASE64_ALPHABET, config.X3_BASE64_ALPHABET)

    def encode(self, data_to_encode):
        if isinstance(data_to_encode, (bytes, bytearray)):
            data_bytes = data_to_encode
        elif isinstance(data_to_encode, str):
            data_bytes = data_to_encode.encode("utf-8")
        else:
            data_bytes = bytearray(data_to_encode)
        standard_encoded = base64.b64encode(data_bytes).decode("utf-8")
        return standard_encoded.translate(self._custom_encode_table)

    def encode_x3(self, input_bytes):
        standard_encoded = base64.b64encode(input_bytes).decode("utf-8")
        return standard_encoded.translate(self._x3_encode_table)


class RandomGenerator:
    def __init__(self):
        self.config = CryptoConfig()

    def generate_random_byte_in_range(self, min_val, max_val):
        return random.randint(min_val, max_val)

    def generate_random_int(self):
        return random.randint(0, self.config.MAX_32BIT)


class CryptoProcessor:
    def __init__(self, config=None):
        self.config = config or CryptoConfig()
        self.bit_ops = BitOperations(self.config)
        self.b64encoder = Base64Encoder(self.config)
        self.random_gen = RandomGenerator()

    def _int_to_le_bytes(self, val, length=4):
        arr = []
        for _ in range(length):
            arr.append(val & 0xFF)
            val >>= 8
        return arr

    def env_fingerprint_a(self, ts, xor_key):
        data = bytearray(struct.pack("<Q", ts))
        sum1 = sum(data[1:5])
        sum2 = sum(data[5:8])
        mark = ((sum1 & 0xFF) + sum2) & 0xFF
        data[0] = mark
        for i in range(len(data)):
            data[i] ^= xor_key
        return list(data)

    def env_fingerprint_b(self, ts):
        return list(struct.pack("<Q", ts))

    def build_payload_array(self, hex_parameter, a1_value, app_identifier="xhs-pc-web", string_param="", timestamp=None):
        payload = []
        payload.extend(self.config.VERSION_BYTES)

        seed = self.random_gen.generate_random_int()
        seed_bytes = self._int_to_le_bytes(seed, 4)
        payload.extend(seed_bytes)
        seed_byte_0 = seed_bytes[0]

        if timestamp is None:
            timestamp = time.time()
        payload.extend(self.env_fingerprint_a(int(timestamp * 1000), self.config.ENV_FINGERPRINT_XOR_KEY))

        time_offset = self.random_gen.generate_random_byte_in_range(
            self.config.ENV_FINGERPRINT_TIME_OFFSET_MIN, self.config.ENV_FINGERPRINT_TIME_OFFSET_MAX
        )
        payload.extend(self.env_fingerprint_b(int((timestamp - time_offset) * 1000)))

        sequence_value = self.random_gen.generate_random_byte_in_range(
            self.config.SEQUENCE_VALUE_MIN, self.config.SEQUENCE_VALUE_MAX
        )
        payload.extend(self._int_to_le_bytes(sequence_value, 4))

        window_props_length = self.random_gen.generate_random_byte_in_range(
            self.config.WINDOW_PROPS_LENGTH_MIN, self.config.WINDOW_PROPS_LENGTH_MAX
        )
        payload.extend(self._int_to_le_bytes(window_props_length, 4))

        uri_length = len(string_param)
        payload.extend(self._int_to_le_bytes(uri_length, 4))

        md5_bytes = bytes.fromhex(hex_parameter)
        for i in range(8):
            payload.append(md5_bytes[i] ^ seed_byte_0)

        payload.append(52)

        a1_bytes = a1_value.encode("utf-8")
        if len(a1_bytes) > 52:
            a1_bytes = a1_bytes[:52]
        elif len(a1_bytes) < 52:
            a1_bytes = a1_bytes + b"\x00" * (52 - len(a1_bytes))
        payload.extend(a1_bytes)

        payload.append(10)

        source_bytes = app_identifier.encode("utf-8")
        if len(source_bytes) > 10:
            source_bytes = source_bytes[:10]
        elif len(source_bytes) < 10:
            source_bytes = source_bytes + b"\x00" * (10 - len(source_bytes))
        payload.extend(source_bytes)

        payload.append(1)
        payload.append(self.config.CHECKSUM_VERSION)
        payload.append(seed_byte_0 ^ self.config.CHECKSUM_XOR_KEY)
        payload.extend(self.config.CHECKSUM_FIXED_TAIL)

        return payload


class CRC32:
    MASK32 = 0xFFFFFFFF
    POLY = 0xEDB88320
    _TABLE = None

    @classmethod
    def _ensure_table(cls):
        if cls._TABLE is not None:
            return
        tbl = [0] * 256
        for d in range(256):
            r = d
            for _ in range(8):
                r = ((r >> 1) ^ cls.POLY) if (r & 1) else (r >> 1)
                r &= cls.MASK32
            tbl[d] = r
        cls._TABLE = tbl

    @classmethod
    def crc32_js_int(cls, data, signed=True):
        cls._ensure_table()
        c = cls.MASK32
        if isinstance(data, str):
            it = (ord(ch) & 0xFF for ch in data)
        else:
            it = data
        for b in it:
            c = (cls._TABLE[((c & 0xFF) ^ b) & 0xFF] ^ (c >> 8)) & cls.MASK32
        u = ((cls.MASK32 ^ c) ^ cls.POLY) & cls.MASK32
        return u - 0x100000000 if (signed and (u & 0x80000000)) else u


class FingerprintGenerator:
    def __init__(self, config):
        self.config = config
        self._b1_key = self.config.B1_SECRET_KEY.encode()
        self._encoder = Base64Encoder(self.config)

    def generate_b1(self, fp):
        b1_fp = {k: fp[k] for k in ["x33", "x34", "x35", "x36", "x37", "x38", "x39", "x42", "x43", "x44", "x45", "x46", "x48", "x49", "x50", "x51", "x52", "x82"]}
        b1_json = json.dumps(b1_fp, separators=(",", ":"), ensure_ascii=False)
        cipher = RC4(self._b1_key)
        ciphertext = cipher.encrypt(b1_json.encode("utf-8")).decode("latin1")
        encoded_url = urllib.parse.quote(ciphertext, safe="!*'()~_-")
        b = []
        for c in encoded_url.split("%")[1:]:
            chars = list(c)
            b.append(int("".join(chars[:2]), 16))
            for j in chars[2:]:
                b.append(ord(j))
        return self._encoder.encode(bytearray(b))

    def generate(self, cookies, user_agent):
        cookie_string = "; ".join(f"{k}={v}" for k, v in cookies.items())
        screen_config = get_screen_config()
        vendor, renderer = get_renderer_info()

        fp = {
            "x1": user_agent,
            "x2": "false",
            "x3": "zh-CN",
            "x4": weighted_random_choice(FPData.COLOR_DEPTH_OPTIONS["values"], FPData.COLOR_DEPTH_OPTIONS["weights"]),
            "x5": weighted_random_choice(FPData.DEVICE_MEMORY_OPTIONS["values"], FPData.DEVICE_MEMORY_OPTIONS["weights"]),
            "x6": "24",
            "x7": f"{vendor},{renderer}",
            "x8": weighted_random_choice(FPData.CORE_OPTIONS["values"], FPData.CORE_OPTIONS["weights"]),
            "x9": f"{screen_config['width']};{screen_config['height']}",
            "x10": f"{screen_config['availWidth']};{screen_config['availHeight']}",
            "x11": "-480",
            "x12": "Asia/Shanghai",
            "x13": "true", "x14": "true", "x15": "true", "x16": "false", "x17": "false",
            "x18": "un",
            "x19": "Win32",
            "x20": "",
            "x21": FPData.BROWSER_PLUGINS,
            "x22": hashlib.md5(secrets.token_bytes(32)).hexdigest(),
            "x23": "false", "x24": "false", "x25": "false", "x26": "false", "x27": "false",
            "x28": "0,false,false",
            "x29": "4,7,8",
            "x30": "swf object not loaded",
            "x33": "0", "x34": "0", "x35": "0",
            "x36": str(random.randint(1, 20)),
            "x37": "0|0|0|0|0|0|0|0|0|1|0|0|0|0|0|0|0|0|1|0|0|0|0|0",
            "x38": "0|0|1|0|1|0|0|0|0|0|1|0|1|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0",
            "x39": 0, "x40": "0", "x41": "0",
            "x42": "3.4.4",
            "x43": FPData.CANVAS_HASH,
            "x44": str(int(time.time() * 1000)),
            "x45": "__SEC_CAV__1-1-1-1-1|__SEC_WSA__|",
            "x46": "false",
            "x47": "1|0|0|0|0|0",
            "x48": "", "x49": "{list:[],type:}", "x50": "", "x51": "", "x52": "",
            "x55": "380,380,360,400,380,400,420,380,400,400,360,360,440,420",
            "x56": f"{vendor}|{renderer}|{hashlib.md5(secrets.token_bytes(32)).hexdigest()}|35",
            "x57": cookie_string,
            "x58": "180", "x59": "2", "x60": "63", "x61": "1291", "x62": "2047",
            "x63": "0", "x64": "0", "x65": "0",
            "x66": {"referer": "", "location": "https://www.xiaohongshu.com/explore", "frame": 0},
            "x67": "1|0", "x68": "0", "x69": "326|1292|30", "x70": ["location"],
            "x71": "true", "x72": "complete", "x73": "1191", "x74": "0|0|0",
            "x75": "Google Inc.", "x76": "true", "x77": "1|1|1|1|1|1|1|1|1|1",
            "x78": {"x": 0, "y": 2400, "left": 0, "right": 290.828125, "bottom": 2418, "height": 18, "top": 2400, "width": 290.828125, "font": FPData.FONTS},
            "x82": "_0x17a2|_0x1954",
            "x31": "124.04347527516074",
            "x79": "144|599565058866",
            "x53": hashlib.md5(secrets.token_bytes(32)).hexdigest(),
            "x54": FPData.VOICE_HASH_OPTIONS,
            "x80": "1|[object FileSystemDirectoryHandle]",
        }
        return fp


class XsCommonSigner:
    def __init__(self, config=None):
        self.config = config or CryptoConfig()
        self._fp_generator = FingerprintGenerator(self.config)
        self._encoder = Base64Encoder(self.config)

    def sign(self, cookie_dict):
        a1_value = cookie_dict["a1"]
        fingerprint = self._fp_generator.generate(cookies=cookie_dict, user_agent=self.config.PUBLIC_USERAGENT)
        b1 = self._fp_generator.generate_b1(fingerprint)
        x9 = CRC32.crc32_js_int(b1)

        sign_struct = dict(self.config.SIGNATURE_XSCOMMON_TEMPLATE)
        sign_struct["x5"] = a1_value
        sign_struct["x8"] = b1
        sign_struct["x9"] = x9

        sign_json = json.dumps(sign_struct, separators=(",", ":"), ensure_ascii=False)
        return self._encoder.encode(sign_json)


def extract_uri(url: str) -> str:
    """从 URL 中提取 URI 路径"""
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    url = url.strip()
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if not path or path == "/":
        raise ValueError(f"Cannot extract valid URI path from URL: {url}")
    return path


class XhsSign:
    """小红书签名生成器"""
    
    def __init__(self, config=None):
        self.config = config or CryptoConfig()
        self.crypto_processor = CryptoProcessor(self.config)

    def _build_content_string(self, method: str, uri: str, payload: Optional[Dict] = None) -> str:
        payload = payload or {}
        if method.upper() == "POST":
            return uri + json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        if not payload:
            return uri
        # GET 请求参数处理 - 列表用逗号连接，=号需要编码
        params = []
        for key, value in payload.items():
            if isinstance(value, (list, tuple)):
                val_str = ",".join(str(v) for v in value)
            elif value is None:
                val_str = ""
            else:
                val_str = str(value)
            # 对值中的 = 号进行编码
            val_str = val_str.replace("=", "%3D")
            params.append(f"{key}={val_str}")
        return f"{uri}?{'&'.join(params)}"

    def _generate_d_value(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _build_signature(self, d_value: str, a1_value: str, xsec_appid: str = "xhs-pc-web", string_param: str = "", timestamp: Optional[float] = None) -> str:
        payload_array = self.crypto_processor.build_payload_array(d_value, a1_value, xsec_appid, string_param, timestamp)
        xor_result = self.crypto_processor.bit_ops.xor_transform_array(payload_array)
        return self.crypto_processor.b64encoder.encode_x3(xor_result[:124])

    def sign_xs_post(self, uri: str, a1_value: str, xsec_appid: str = "xhs-pc-web", payload: Optional[Dict] = None, timestamp: Optional[float] = None) -> str:
        """生成 POST 请求的 x-s 签名"""
        return self.sign_xs("POST", uri, a1_value, xsec_appid, payload=payload, timestamp=timestamp)

    def sign_xs_common(self, cookie_dict: Dict[str, str]) -> str:
        parsed = self._parse_cookies(cookie_dict)
        signer = XsCommonSigner(self.config)
        return signer.sign(parsed)

    def get_x_t(self, timestamp: Optional[float] = None) -> int:
        if timestamp is None:
            timestamp = time.time()
        return int(timestamp * 1000)

    def _parse_cookies(self, cookies):
        if isinstance(cookies, str):
            ck = SimpleCookie()
            ck.load(cookies)
            return {k: morsel.value for k, morsel in ck.items()}
        return cookies

    def sign_xs(self, method: str, uri: str, a1_value: str, xsec_appid: str = "xhs-pc-web", payload: Optional[Dict] = None, timestamp: Optional[float] = None) -> str:
        """生成请求的 x-s 签名（通用方法）"""
        uri = extract_uri(uri)
        signature_data = dict(self.crypto_processor.config.SIGNATURE_DATA_TEMPLATE)
        content_string = self._build_content_string(method, uri, payload)
        d_value = self._generate_d_value(content_string)
        signature_data["x3"] = self.crypto_processor.config.X3_PREFIX + self._build_signature(d_value, a1_value, xsec_appid, content_string, timestamp)
        return self.crypto_processor.config.XYS_PREFIX + self.crypto_processor.b64encoder.encode(json.dumps(signature_data, separators=(",", ":"), ensure_ascii=False))
    
    def sign_xs_get(self, uri: str, a1_value: str, xsec_appid: str = "xhs-pc-web", params: Optional[Dict] = None, timestamp: Optional[float] = None) -> str:
        """生成 GET 请求的 x-s 签名"""
        return self.sign_xs("GET", uri, a1_value, xsec_appid, payload=params, timestamp=timestamp)

    def get_b3_trace_id(self) -> str:
        """生成 x-b3-traceid"""
        return ''.join(random.choices('0123456789abcdef', k=16))
    
    def get_xray_trace_id(self, timestamp_ms: Optional[int] = None) -> str:
        """生成 x-xray-traceid"""
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)
        
        # 格式: timestamp_hex(12) + seq_hex(5) + random_hex(15)
        ts_hex = hex(timestamp_ms)[2:].zfill(12)[:12]
        seq = random.randint(0, 0x7FFFFF)
        seq_hex = hex(seq)[2:].zfill(5)
        rand_hex = ''.join(random.choices('0123456789abcdef', k=15))
        return ts_hex + seq_hex + rand_hex

    def sign_headers_get(self, uri: str, cookies, xsec_appid: str = "xhs-pc-web", params: Optional[Dict] = None, timestamp: Optional[float] = None) -> Dict[str, str]:
        """生成 GET 请求的签名头"""
        if timestamp is None:
            timestamp = time.time()

        cookie_dict = self._parse_cookies(cookies)
        a1_value = cookie_dict.get("a1")
        if not a1_value:
            raise ValueError("Missing 'a1' in cookies")

        x_s = self.sign_xs_get(uri, a1_value, xsec_appid, params=params, timestamp=timestamp)
        x_s_common = self.sign_xs_common(cookie_dict)
        x_t = self.get_x_t(timestamp)

        return {
            "x-s": x_s,
            "x-s-common": x_s_common,
            "x-t": str(x_t),
            "x-b3-traceid": self.get_b3_trace_id(),
            "x-xray-traceid": self.get_xray_trace_id(int(timestamp * 1000)),
        }

    def sign_headers_post(self, uri: str, cookies, xsec_appid: str = "xhs-pc-web", payload: Optional[Dict] = None, timestamp: Optional[float] = None) -> Dict[str, str]:
        """生成 POST 请求的签名头"""
        if timestamp is None:
            timestamp = time.time()

        cookie_dict = self._parse_cookies(cookies)
        a1_value = cookie_dict.get("a1")
        if not a1_value:
            raise ValueError("Missing 'a1' in cookies")

        x_s = self.sign_xs_post(uri, a1_value, xsec_appid, payload=payload, timestamp=timestamp)
        x_s_common = self.sign_xs_common(cookie_dict)
        x_t = self.get_x_t(timestamp)

        return {
            "x-s": x_s,
            "x-s-common": x_s_common,
            "x-t": str(x_t),
            "x-b3-traceid": self.get_b3_trace_id(),
            "x-xray-traceid": self.get_xray_trace_id(int(timestamp * 1000)),
        }


# 单例实例
_signer = XhsSign()


def generate_sign_headers(cookie: str, note_id: str, xsec_token: str, xsec_source: str = "pc_user") -> Dict[str, str]:
    """
    生成小红书 API 请求签名头
    
    Args:
        cookie: 小红书 Cookie 字符串
        note_id: 笔记 ID
        xsec_token: 安全令牌
        
    Returns:
        签名头字典 {x-s, x-s-common, x-t}
    """
    api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/feed"
    payload = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": "1"},
        "xsec_source": xsec_source,
        "xsec_token": xsec_token,
    }
    
    headers = _signer.sign_headers_post(api_url, cookies=cookie, payload=payload)
    _debug_kv("sign_headers_keys", list(headers.keys()))
    _debug_kv("x-s_len", len(headers.get("x-s", "")))
    _debug_kv("x-s-common_len", len(headers.get("x-s-common", "")))
    return headers

# ==================== 采集核心逻辑 ====================

def extract_note_id_from_url(note_url):
    """从笔记 URL 中提取笔记 ID"""
    note_url = note_url.strip()
    for pattern in (r'/explore/([a-zA-Z0-9]+)', r'/discovery/item/([a-zA-Z0-9]+)'):
        match = re.search(pattern, note_url)
        if match:
            return match.group(1)
    raise ValueError(f"无法从 URL 中提取笔记 ID: {note_url}")


def _extract_query_param(note_url, key):
    """从 URL 查询参数中提取值（避免 + 被转为空格）"""
    query = urllib.parse.urlparse(note_url).query
    if not query:
        return ""
    for pair in query.split("&"):
        if not pair:
            continue
        param_key, _, value = pair.partition("=")
        if param_key == key:
            return urllib.parse.unquote(value)
    return ""


def extract_xsec_token_from_url(note_url):
    """从笔记 URL 中提取 xsec_token"""
    return _extract_query_param(note_url, "xsec_token") or ""


def extract_xsec_source_from_url(note_url):
    """从笔记 URL 中提取 xsec_source"""
    return _extract_query_param(note_url, "xsec_source") or ""


def extract_xsec_token_from_html(html_content, note_id=""):
    """从笔记详情页 HTML 中提取 xsec_token"""
    patterns = []
    if note_id:
        patterns.extend([
            rf'"note_id"\s*:\s*"{note_id}".+?"xsec_token"\s*:\s*"([^"]+)"',
            rf'"noteId"\s*:\s*"{note_id}".+?"xsecToken"\s*:\s*"([^"]+)"',
        ])
    patterns.extend([
        r'"xsec_token"\s*:\s*"([^"]+)"',
        r'"xsecToken"\s*:\s*"([^"]+)"',
    ])
    for pattern in patterns:
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            return match.group(1)
    return ""


def fetch_note_html(note_url, cookie, user_agent):
    """获取笔记详情页 HTML"""
    _debug_kv("fetch_note_html_url", note_url.split("?")[0])
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "max-age=0",
        "upgrade-insecure-requests": "1",
        "user-agent": user_agent,
        "cookie": cookie,
        "referer": "https://www.xiaohongshu.com/"
    }

    response = requests.get(note_url, headers=headers, allow_redirects=True, timeout=30)
    _debug_kv("fetch_note_html_status", response.status_code)
    _debug_kv("fetch_note_html_length", len(response.text))

    if response.status_code != 200:
        raise Exception(f"请求笔记详情页失败: HTTP {response.status_code}")

    return response.text


def fetch_note_detail(note_id, xsec_token, xsec_source, cookie, user_agent):
    """获取笔记详情数据"""
    api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/feed"

    _debug_kv("fetch_note_detail_note_id", note_id)
    _debug_kv("fetch_note_detail_xsec_source", xsec_source)
    _debug_kv("fetch_note_detail_xsec_token_len", len(xsec_token) if xsec_token else 0)
    if xsec_token and any(ch.isspace() for ch in xsec_token):
        _debug("[debug] xsec_token has whitespace")

    payload = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": "1"},
        "xsec_source": xsec_source,
        "xsec_token": xsec_token,
    }

    # 生成签名
    sign_headers = generate_sign_headers(cookie, note_id, xsec_token, xsec_source)

    payload_debug = dict(payload)
    payload_debug["xsec_token"] = _mask(xsec_token)
    _debug_kv("feed_payload", payload_debug)

    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": f"https://www.xiaohongshu.com/explore/{note_id}",
        "User-Agent": user_agent,
        "Cookie": cookie,
    }
    headers.update(sign_headers)

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    _debug_kv("feed_body_len", len(body))
    response = requests.post(api_url, headers=headers, data=body.encode("utf-8"), timeout=30)
    _debug_kv("feed_http_status", response.status_code)

    if response.status_code == 406:
        _debug_kv("feed_response_text", response.text[:500])
        raise Exception("签名验证失败 (406)")

    if response.status_code != 200:
        _debug_kv("feed_response_text", response.text[:500])
        raise Exception(f"feed 请求失败: HTTP {response.status_code}")

    data = response.json()
    _debug_kv("feed_code", data.get("code"))
    _debug_kv("feed_msg", data.get("msg"))

    if data.get("code") == -100:
        raise Exception("Cookie 已失效，请重新获取")

    if data.get("code") != 0:
        raise Exception(f"feed 返回异常: {data.get('msg', data.get('code', 'unknown'))}")

    return data


def extract_video_url(video_info):
    """提取视频链接"""
    if not isinstance(video_info, dict):
        return ""

    def find_url(value):
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("http"):
                return text
            if text.startswith("//"):
                return f"https:{text}"
            if text.endswith((".mp4", ".mov", ".m3u8")):
                return f"https://sns-video-qc.xhscdn.com/{text.lstrip('/')}"
            return ""
        if isinstance(value, list):
            for item in value:
                url = find_url(item)
                if url:
                    return url
            return ""
        if isinstance(value, dict):
            priority_keys = (
                "origin_video_key", "originVideoKey", "url", "url_default",
                "url_pre", "urlPre", "download_url", "origin_url", "stream_url",
            )
            for key in priority_keys:
                if key in value:
                    url = find_url(value.get(key))
                    if url:
                        return url
            for sub_value in value.values():
                url = find_url(sub_value)
                if url:
                    return url
        return ""

    return find_url(video_info)


def extract_image_url(image_info):
    """提取图片链接"""
    if not isinstance(image_info, dict):
        return ""
    for key in ("url_default", "url_pre", "url", "urlDefault", "urlPre"):
        url = image_info.get(key)
        if url:
            return url
    return ""


def process_note_detail(feed_data, note_id, xsec_token, xsec_source="pc_user"):
    """处理笔记详情，转换为飞书表格记录格式"""
    items = feed_data.get("data", {}).get("items", [])

    if not items:
        raise Exception("feed 响应中没有找到笔记数据")

    note_item = items[0]
    note_card = note_item.get("note_card", {})

    user = note_card.get("user", {})
    interact_info = note_card.get("interact_info", {})
    image_list = note_card.get("image_list", [])
    tag_list = note_card.get("tag_list", [])
    video = note_card.get("video", {})

    # 图片链接（多张用换行分隔）
    image_text = "\n".join(
        img.get("url_default") or img.get("url_pre") or img.get("url", "")
        for img in image_list
        if img.get("url_default") or img.get("url_pre") or img.get("url")
    )

    # 笔记封面图
    cover_url = extract_image_url(note_card.get("cover", {}))
    if not cover_url and image_list:
        cover_url = extract_image_url(image_list[0])

    # 标签数组（仅提取话题标签）
    tags_array = [
        tag.get("name", "")
        for tag in tag_list
        if tag.get("type") == "topic" and tag.get("name")
    ]

    # 视频链接
    video_url = extract_video_url(video)

    # 互动数据
    liked_count = int(interact_info.get("liked_count", 0) or 0)
    collected_count = int(interact_info.get("collected_count", 0) or 0)
    comment_count = int(interact_info.get("comment_count", 0) or 0)
    share_count = int(interact_info.get("share_count", 0) or 0)

    # 发布时间
    publish_time = note_card.get("time", 0)

    # 笔记链接
    note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"

    # 用户信息
    user_nickname = user.get("nickname") or user.get("nickName") or user.get("nick_name") or ""
    user_id = user.get("user_id") or user.get("userId") or ""
    user_avatar = user.get("avatar") or user.get("avatar_url") or user.get("avatarUrl") or ""
    user_home_page = f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else ""

    return {
        "fields": {
            "图片链接": image_text,
            "笔记封面图链接": cover_url,
            "笔记标题": note_card.get("title") or note_card.get("display_title", ""),
            "笔记内容": note_card.get("desc", ""),
            "笔记类型": note_card.get("type", ""),
            "笔记链接": note_url,
            "笔记标签": tags_array,
            "账号名称": user_nickname,
            "主页链接": user_home_page,
            "头像链接": user_avatar,
            "分享数": share_count,
            "点赞数": liked_count,
            "收藏数": collected_count,
            "评论数": comment_count,
            "视频链接": video_url,
            "发布时间": publish_time
        }
    }


# ==================== Coze 入口函数 ====================

async def main(args):
    """
    Coze 代码节点入口函数

    输入参数（从 args.params 获取）：
    - bijilianjie: 笔记链接
    - cookie: 小红书 Cookie

    返回：
    - records: 飞书多维表格记录数组
    """
    params = getattr(args, "params", {}) or {}

    def _get_param(source, name):
        if isinstance(source, dict):
            return source.get(name)
        return getattr(source, name, None)

    debug_param = _get_param(params, "debug")
    debug_enabled = _boolish(debug_param) if debug_param is not None else True
    _set_debug(debug_enabled)
    _debug_kv("debug_enabled", debug_enabled)

    # 获取输入参数（兼容 dict 和属性两种写法）
    note_url = (
        _get_param(params, "bijilianjie")
        or _get_param(params, "note_url")
        or _get_param(params, "noteUrl")
    )
    cookie = _get_param(params, "cookie")

    if not note_url:
        raise ValueError("缺少笔记链接 bijilianjie，请在开始节点输入完整链接")
    if not cookie:
        raise ValueError("缺少 cookie，请在开始节点输入小红书 Cookie")

    note_url = str(note_url).strip()
    if not note_url.startswith("http"):
        raise ValueError("笔记链接格式不正确，请复制完整的笔记 URL（包含 https://.../explore/...）")
    cookie = str(cookie).strip().replace("\r", "").replace("\n", "")
    _debug_kv("note_url_base", note_url.split("?")[0])
    _debug_kv("cookie_len", len(cookie))
    _debug_kv("cookie_has_a1", "a1=" in cookie)

    # 默认 User-Agent（与签名指纹保持一致）
    user_agent = _signer.config.PUBLIC_USERAGENT

    # 1. 从 URL 提取 note_id
    note_id = extract_note_id_from_url(note_url)
    _debug_kv("note_id", note_id)

    # 2. 从 URL 提取 xsec_token 和 xsec_source
    xsec_token = extract_xsec_token_from_url(note_url)
    xsec_source = extract_xsec_source_from_url(note_url) or "pc_user"
    if xsec_token and any(ch.isspace() for ch in xsec_token):
        _debug("[debug] xsec_token has whitespace, cleaning")
        xsec_token = "".join(xsec_token.split())
    _debug_kv("xsec_source", xsec_source)
    _debug_kv("xsec_token_len", len(xsec_token) if xsec_token else 0)

    # 3. 如果 URL 中没有 xsec_token，从 HTML 中提取
    if not xsec_token:
        _debug("[debug] xsec_token missing in URL, fetching HTML")
        html_content = fetch_note_html(note_url, cookie, user_agent)
        xsec_token = extract_xsec_token_from_html(html_content, note_id)
        if xsec_token and any(ch.isspace() for ch in xsec_token):
            _debug("[debug] xsec_token from HTML has whitespace, cleaning")
            xsec_token = "".join(xsec_token.split())
        _debug_kv("xsec_token_from_html_len", len(xsec_token) if xsec_token else 0)

    if not xsec_token:
        raise ValueError("笔记链接缺少 xsec_token，请提供完整链接")

    # 4. 获取笔记详情（遇到“参数无效”时尝试刷新 xsec_token 再试一次）
    try:
        feed_data = fetch_note_detail(note_id, xsec_token, xsec_source, cookie, user_agent)
    except Exception as e:
        if "参数无效" in str(e):
            _debug("[debug] feed returned 参数无效, refresh token and retry")
            html_content = fetch_note_html(note_url, cookie, user_agent)
            refreshed_token = extract_xsec_token_from_html(html_content, note_id)
            if refreshed_token and refreshed_token != xsec_token:
                if any(ch.isspace() for ch in refreshed_token):
                    _debug("[debug] refreshed xsec_token has whitespace, cleaning")
                    refreshed_token = "".join(refreshed_token.split())
                xsec_token = refreshed_token
                _debug_kv("refreshed_xsec_token_len", len(xsec_token))
                feed_data = fetch_note_detail(note_id, xsec_token, xsec_source, cookie, user_agent)
            else:
                raise Exception("参数无效：请用网页版打开笔记，复制完整链接，并更新 Cookie 后再试") from e
        else:
            raise

    # 5. 处理数据，转换为飞书表格格式
    record = process_note_detail(feed_data, note_id, xsec_token, xsec_source)

    # 6. 返回 records 数组
    return {
        "records": [record]
    }
