// 小红书单条笔记采集 - Coze 兼容版本
// 不使用 btoa、TextEncoder 等浏览器专有 API
// 输入参数: bijilianjie, cookie
// 输出: records

// ==================== 纯 JS 实现的工具函数 ====================

// 纯 JS 实现 TextEncoder
function stringToBytes(str) {
    const bytes = [];
    for (let i = 0; i < str.length; i++) {
        let code = str.charCodeAt(i);
        if (code < 0x80) {
            bytes.push(code);
        } else if (code < 0x800) {
            bytes.push(0xC0 | (code >> 6), 0x80 | (code & 0x3F));
        } else if (code < 0x10000) {
            bytes.push(0xE0 | (code >> 12), 0x80 | ((code >> 6) & 0x3F), 0x80 | (code & 0x3F));
        } else {
            bytes.push(
                0xF0 | (code >> 18),
                0x80 | ((code >> 12) & 0x3F),
                0x80 | ((code >> 6) & 0x3F),
                0x80 | (code & 0x3F)
            );
        }
    }
    return new Uint8Array(bytes);
}

// 纯 JS 实现 Base64 编码
function bytesToBase64(bytes) {
    const base64abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let result = '';
    let i;
    const l = bytes.length;
    for (i = 2; i < l; i += 3) {
        result += base64abc[bytes[i - 2] >> 2];
        result += base64abc[((bytes[i - 2] & 0x03) << 4) | (bytes[i - 1] >> 4)];
        result += base64abc[((bytes[i - 1] & 0x0F) << 2) | (bytes[i] >> 6)];
        result += base64abc[bytes[i] & 0x3F];
    }
    if (i === l + 1) {
        result += base64abc[bytes[i - 2] >> 2];
        result += base64abc[(bytes[i - 2] & 0x03) << 4];
        result += "==";
    }
    if (i === l) {
        result += base64abc[bytes[i - 2] >> 2];
        result += base64abc[((bytes[i - 2] & 0x03) << 4) | (bytes[i - 1] >> 4)];
        result += base64abc[(bytes[i - 1] & 0x0F) << 2];
        result += "=";
    }
    return result;
}

function stringToBase64(str) {
    return bytesToBase64(stringToBytes(str));
}

// ==================== RC4 加密 ====================
class RC4 {
    constructor(keyBytes) {
        this._key = keyBytes;
    }

    encrypt(plaintext) {
        const key = this._key;
        const s = Array.from({ length: 256 }, (_, i) => i);
        let j = 0;
        for (let i = 0; i < 256; i++) {
            j = (j + s[i] + key[i % key.length]) % 256;
            [s[i], s[j]] = [s[j], s[i]];
        }

        let i = 0;
        j = 0;
        const out = [];
        for (const byte of plaintext) {
            i = (i + 1) % 256;
            j = (j + s[i]) % 256;
            [s[i], s[j]] = [s[j], s[i]];
            const k = s[(s[i] + s[j]) % 256];
            out.push(byte ^ k);
        }
        return new Uint8Array(out);
    }
}

// ==================== 浏览器指纹数据 ====================
const FPData = {
    GPU_VENDORS: [
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 520 (0x1912) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00003EA0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB (0x000010DE) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ],
    SCREEN_RESOLUTIONS: { resolutions: ["1366;768", "1600;900", "1920;1080", "2560;1440"], weights: [0.25, 0.15, 0.45, 0.15] },
    COLOR_DEPTH_OPTIONS: { values: [24, 32], weights: [0.7, 0.3] },
    DEVICE_MEMORY_OPTIONS: { values: [4, 8, 16], weights: [0.4, 0.4, 0.2] },
    CORE_OPTIONS: { values: [4, 6, 8], weights: [0.5, 0.3, 0.2] },
    BROWSER_PLUGINS: "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
    CANVAS_HASH: "742cc32c",
    VOICE_HASH_OPTIONS: "10311144241322244122",
    FONTS: 'system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif'
};

function weightedRandomChoice(options, weights) {
    const totalWeight = weights.reduce((a, b) => a + b, 0);
    let random = Math.random() * totalWeight;
    for (let i = 0; i < options.length; i++) {
        random -= weights[i];
        if (random <= 0) return String(options[i]);
    }
    return String(options[options.length - 1]);
}

function getRendererInfo() {
    const rendererStr = FPData.GPU_VENDORS[Math.floor(Math.random() * FPData.GPU_VENDORS.length)];
    const [vendor, renderer] = rendererStr.split("|");
    return { vendor, renderer };
}

function getScreenConfig() {
    const resolution = weightedRandomChoice(FPData.SCREEN_RESOLUTIONS.resolutions, FPData.SCREEN_RESOLUTIONS.weights);
    const [widthStr, heightStr] = resolution.split(";");
    const width = parseInt(widthStr);
    const height = parseInt(heightStr);
    const offsets = [0, 30, 60];
    const heightOffsets = [30, 60, 80];
    const availWidth = width - offsets[Math.floor(Math.random() * offsets.length)];
    const availHeight = height - heightOffsets[Math.floor(Math.random() * heightOffsets.length)];
    return { width, height, availWidth, availHeight };
}

// ==================== 加密配置 ====================
const CryptoConfig = {
    MAX_32BIT: 0xFFFFFFFF,
    STANDARD_BASE64_ALPHABET: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    CUSTOM_BASE64_ALPHABET: "ZmserbBoHQtNP+wOcza/LpngG8yJq42KWYj0DSfdikx3VT16IlUAFM97hECvuRX5",
    X3_BASE64_ALPHABET: "MfgqrsbcyzPQRStuvC7mn501HIJBo2DEFTKdeNOwxWXYZap89+/A4UVLhijkl63G",
    HEX_KEY: "71a302257793271ddd273bcee3e4b98d9d7935e1da33f5765e2ea8afb6dc77a51a499d23b67c20660025860cbf13d4540d92497f58686c574e508f46e1956344f39139bf4faf22a3eef120b79258145b2feb5193b6478669961298e79bedca646e1a693a926154a5a7a1bd1cf0dedb742f917a747a1e388b234f2277",
    VERSION_BYTES: [119, 104, 96, 41],
    SEQUENCE_VALUE_MIN: 15,
    SEQUENCE_VALUE_MAX: 50,
    WINDOW_PROPS_LENGTH_MIN: 900,
    WINDOW_PROPS_LENGTH_MAX: 1200,
    CHECKSUM_VERSION: 1,
    CHECKSUM_XOR_KEY: 115,
    CHECKSUM_FIXED_TAIL: [249, 65, 103, 103, 201, 181, 131, 99, 94, 7, 68, 250, 132, 21],
    ENV_FINGERPRINT_XOR_KEY: 41,
    ENV_FINGERPRINT_TIME_OFFSET_MIN: 10,
    ENV_FINGERPRINT_TIME_OFFSET_MAX: 50,
    SIGNATURE_DATA_TEMPLATE: { x0: "4.2.6", x1: "xhs-pc-web", x2: "Windows", x3: "", x4: "" },
    X3_PREFIX: "mns0301_",
    XYS_PREFIX: "XYS_",
    B1_SECRET_KEY: "xhswebmplfbt",
    SIGNATURE_XSCOMMON_TEMPLATE: {
        s0: 5, s1: "", x0: "1", x1: "4.2.6", x2: "Windows",
        x3: "xhs-pc-web", x4: "4.86.0", x5: "", x6: "", x7: "",
        x8: "", x9: -596800761, x10: 0, x11: "normal"
    },
    PUBLIC_USERAGENT: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
};

// ==================== 工具函数 ====================
function hexToBytes(hex) {
    const bytes = [];
    for (let i = 0; i < hex.length; i += 2) {
        bytes.push(parseInt(hex.substr(i, 2), 16));
    }
    return new Uint8Array(bytes);
}

function bytesToHex(bytes) {
    return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

function md5(str) {
    function md5cycle(x, k) {
        let a = x[0], b = x[1], c = x[2], d = x[3];
        a = ff(a, b, c, d, k[0], 7, -680876936);
        d = ff(d, a, b, c, k[1], 12, -389564586);
        c = ff(c, d, a, b, k[2], 17, 606105819);
        b = ff(b, c, d, a, k[3], 22, -1044525330);
        a = ff(a, b, c, d, k[4], 7, -176418897);
        d = ff(d, a, b, c, k[5], 12, 1200080426);
        c = ff(c, d, a, b, k[6], 17, -1473231341);
        b = ff(b, c, d, a, k[7], 22, -45705983);
        a = ff(a, b, c, d, k[8], 7, 1770035416);
        d = ff(d, a, b, c, k[9], 12, -1958414417);
        c = ff(c, d, a, b, k[10], 17, -42063);
        b = ff(b, c, d, a, k[11], 22, -1990404162);
        a = ff(a, b, c, d, k[12], 7, 1804603682);
        d = ff(d, a, b, c, k[13], 12, -40341101);
        c = ff(c, d, a, b, k[14], 17, -1502002290);
        b = ff(b, c, d, a, k[15], 22, 1236535329);
        a = gg(a, b, c, d, k[1], 5, -165796510);
        d = gg(d, a, b, c, k[6], 9, -1069501632);
        c = gg(c, d, a, b, k[11], 14, 643717713);
        b = gg(b, c, d, a, k[0], 20, -373897302);
        a = gg(a, b, c, d, k[5], 5, -701558691);
        d = gg(d, a, b, c, k[10], 9, 38016083);
        c = gg(c, d, a, b, k[15], 14, -660478335);
        b = gg(b, c, d, a, k[4], 20, -405537848);
        a = gg(a, b, c, d, k[9], 5, 568446438);
        d = gg(d, a, b, c, k[14], 9, -1019803690);
        c = gg(c, d, a, b, k[3], 14, -187363961);
        b = gg(b, c, d, a, k[8], 20, 1163531501);
        a = gg(a, b, c, d, k[13], 5, -1444681467);
        d = gg(d, a, b, c, k[2], 9, -51403784);
        c = gg(c, d, a, b, k[7], 14, 1735328473);
        b = gg(b, c, d, a, k[12], 20, -1926607734);
        a = hh(a, b, c, d, k[5], 4, -378558);
        d = hh(d, a, b, c, k[8], 11, -2022574463);
        c = hh(c, d, a, b, k[11], 16, 1839030562);
        b = hh(b, c, d, a, k[14], 23, -35309556);
        a = hh(a, b, c, d, k[1], 4, -1530992060);
        d = hh(d, a, b, c, k[4], 11, 1272893353);
        c = hh(c, d, a, b, k[7], 16, -155497632);
        b = hh(b, c, d, a, k[10], 23, -1094730640);
        a = hh(a, b, c, d, k[13], 4, 681279174);
        d = hh(d, a, b, c, k[0], 11, -358537222);
        c = hh(c, d, a, b, k[3], 16, -722521979);
        b = hh(b, c, d, a, k[6], 23, 76029189);
        a = hh(a, b, c, d, k[9], 4, -640364487);
        d = hh(d, a, b, c, k[12], 11, -421815835);
        c = hh(c, d, a, b, k[15], 16, 530742520);
        b = hh(b, c, d, a, k[2], 23, -995338651);
        a = ii(a, b, c, d, k[0], 6, -198630844);
        d = ii(d, a, b, c, k[7], 10, 1126891415);
        c = ii(c, d, a, b, k[14], 15, -1416354905);
        b = ii(b, c, d, a, k[5], 21, -57434055);
        a = ii(a, b, c, d, k[12], 6, 1700485571);
        d = ii(d, a, b, c, k[3], 10, -1894986606);
        c = ii(c, d, a, b, k[10], 15, -1051523);
        b = ii(b, c, d, a, k[1], 21, -2054922799);
        a = ii(a, b, c, d, k[8], 6, 1873313359);
        d = ii(d, a, b, c, k[15], 10, -30611744);
        c = ii(c, d, a, b, k[6], 15, -1560198380);
        b = ii(b, c, d, a, k[13], 21, 1309151649);
        a = ii(a, b, c, d, k[4], 6, -145523070);
        d = ii(d, a, b, c, k[11], 10, -1120210379);
        c = ii(c, d, a, b, k[2], 15, 718787259);
        b = ii(b, c, d, a, k[9], 21, -343485551);
        x[0] = add32(a, x[0]);
        x[1] = add32(b, x[1]);
        x[2] = add32(c, x[2]);
        x[3] = add32(d, x[3]);
    }
    function cmn(q, a, b, x, s, t) {
        a = add32(add32(a, q), add32(x, t));
        return add32((a << s) | (a >>> (32 - s)), b);
    }
    function ff(a, b, c, d, x, s, t) { return cmn((b & c) | ((~b) & d), a, b, x, s, t); }
    function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & (~d)), a, b, x, s, t); }
    function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
    function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | (~d)), a, b, x, s, t); }
    function add32(a, b) { return (a + b) & 0xFFFFFFFF; }
    function md5blk(s) {
        const md5blks = [];
        for (let i = 0; i < 64; i += 4) {
            md5blks[i >> 2] = s.charCodeAt(i) + (s.charCodeAt(i + 1) << 8) + (s.charCodeAt(i + 2) << 16) + (s.charCodeAt(i + 3) << 24);
        }
        return md5blks;
    }
    function rhex(n) {
        const hex_chr = '0123456789abcdef';
        let s = '';
        for (let j = 0; j < 4; j++) {
            s += hex_chr.charAt((n >> (j * 8 + 4)) & 0x0F) + hex_chr.charAt((n >> (j * 8)) & 0x0F);
        }
        return s;
    }
    function hex(x) { return x.map(rhex).join(''); }
    function md5str(s) {
        const n = s.length;
        let state = [1732584193, -271733879, -1732584194, 271733878];
        let i;
        for (i = 64; i <= s.length; i += 64) {
            md5cycle(state, md5blk(s.substring(i - 64, i)));
        }
        s = s.substring(i - 64);
        const tail = new Array(16).fill(0);
        for (i = 0; i < s.length; i++) {
            tail[i >> 2] |= s.charCodeAt(i) << ((i % 4) << 3);
        }
        tail[i >> 2] |= 0x80 << ((i % 4) << 3);
        if (i > 55) {
            md5cycle(state, tail);
            tail.fill(0);
        }
        tail[14] = n * 8;
        md5cycle(state, tail);
        return hex(state);
    }
    return md5str(str);
}

function randomBytes(length) {
    const bytes = new Uint8Array(length);
    for (let i = 0; i < length; i++) {
        bytes[i] = Math.floor(Math.random() * 256);
    }
    return bytes;
}

function randomHex(length) {
    return bytesToHex(randomBytes(length));
}

// ==================== 自定义 Base64 编码 ====================
function customBase64Encode(data, alphabet) {
    const standard = CryptoConfig.STANDARD_BASE64_ALPHABET + "=";
    const custom = alphabet + "=";

    // 先用纯 JS 转为标准 Base64
    const base64 = bytesToBase64(data);

    // 字符替换
    let result = '';
    for (const char of base64) {
        const idx = standard.indexOf(char);
        result += idx >= 0 ? custom[idx] : char;
    }
    return result;
}

function base64Encode(data) {
    if (typeof data === 'string') {
        return customBase64Encode(stringToBytes(data), CryptoConfig.CUSTOM_BASE64_ALPHABET);
    }
    return customBase64Encode(data, CryptoConfig.CUSTOM_BASE64_ALPHABET);
}

function base64EncodeX3(data) {
    return customBase64Encode(data, CryptoConfig.X3_BASE64_ALPHABET);
}

// ==================== 位操作 ====================
function xorTransformArray(sourceIntegers) {
    const keyBytes = hexToBytes(CryptoConfig.HEX_KEY);
    const result = new Uint8Array(sourceIntegers.length);
    for (let i = 0; i < sourceIntegers.length; i++) {
        if (i < keyBytes.length) {
            result[i] = (sourceIntegers[i] ^ keyBytes[i]) & 0xFF;
        } else {
            result[i] = sourceIntegers[i] & 0xFF;
        }
    }
    return result;
}

function intToLeBytes(val, length = 4) {
    const arr = [];
    for (let i = 0; i < length; i++) {
        arr.push(val & 0xFF);
        val = Math.floor(val / 256);
    }
    return arr;
}

function envFingerprintA(ts, xorKey) {
    const data = new Uint8Array(8);
    let temp = ts;
    for (let i = 0; i < 8; i++) {
        data[i] = temp & 0xFF;
        temp = Math.floor(temp / 256);
    }
    let sum1 = 0;
    for (let i = 1; i < 5; i++) sum1 += data[i];
    let sum2 = 0;
    for (let i = 5; i < 8; i++) sum2 += data[i];
    const mark = ((sum1 & 0xFF) + sum2) & 0xFF;
    data[0] = mark;
    for (let i = 0; i < data.length; i++) {
        data[i] ^= xorKey;
    }
    return Array.from(data);
}

function envFingerprintB(ts) {
    const data = new Uint8Array(8);
    let temp = ts;
    for (let i = 0; i < 8; i++) {
        data[i] = temp & 0xFF;
        temp = Math.floor(temp / 256);
    }
    return Array.from(data);
}

function randomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ==================== 构建 Payload ====================
function buildPayloadArray(hexParameter, a1Value, appIdentifier = "xhs-pc-web", stringParam = "", timestamp = null) {
    const payload = [];
    payload.push(...CryptoConfig.VERSION_BYTES);

    const seed = Math.floor(Math.random() * CryptoConfig.MAX_32BIT);
    const seedBytes = intToLeBytes(seed, 4);
    payload.push(...seedBytes);
    const seedByte0 = seedBytes[0];

    if (timestamp === null) {
        timestamp = Date.now() / 1000;
    }
    payload.push(...envFingerprintA(Math.floor(timestamp * 1000), CryptoConfig.ENV_FINGERPRINT_XOR_KEY));

    const timeOffset = randomInt(CryptoConfig.ENV_FINGERPRINT_TIME_OFFSET_MIN, CryptoConfig.ENV_FINGERPRINT_TIME_OFFSET_MAX);
    payload.push(...envFingerprintB(Math.floor((timestamp - timeOffset) * 1000)));

    const sequenceValue = randomInt(CryptoConfig.SEQUENCE_VALUE_MIN, CryptoConfig.SEQUENCE_VALUE_MAX);
    payload.push(...intToLeBytes(sequenceValue, 4));

    const windowPropsLength = randomInt(CryptoConfig.WINDOW_PROPS_LENGTH_MIN, CryptoConfig.WINDOW_PROPS_LENGTH_MAX);
    payload.push(...intToLeBytes(windowPropsLength, 4));

    const uriLength = stringParam.length;
    payload.push(...intToLeBytes(uriLength, 4));

    const md5Bytes = hexToBytes(hexParameter);
    for (let i = 0; i < 8; i++) {
        payload.push(md5Bytes[i] ^ seedByte0);
    }

    payload.push(52);

    const a1Bytes = stringToBytes(a1Value);
    const a1Padded = new Uint8Array(52);
    for (let i = 0; i < Math.min(a1Bytes.length, 52); i++) {
        a1Padded[i] = a1Bytes[i];
    }
    payload.push(...a1Padded);

    payload.push(10);

    const sourceBytes = stringToBytes(appIdentifier);
    const sourcePadded = new Uint8Array(10);
    for (let i = 0; i < Math.min(sourceBytes.length, 10); i++) {
        sourcePadded[i] = sourceBytes[i];
    }
    payload.push(...sourcePadded);

    payload.push(1);
    payload.push(CryptoConfig.CHECKSUM_VERSION);
    payload.push(seedByte0 ^ CryptoConfig.CHECKSUM_XOR_KEY);
    payload.push(...CryptoConfig.CHECKSUM_FIXED_TAIL);

    return payload;
}

// ==================== CRC32 ====================
const CRC32 = {
    MASK32: 0xFFFFFFFF,
    POLY: 0xEDB88320,
    _TABLE: null,

    _ensureTable() {
        if (this._TABLE) return;
        this._TABLE = new Array(256);
        for (let d = 0; d < 256; d++) {
            let r = d;
            for (let i = 0; i < 8; i++) {
                r = (r & 1) ? ((r >>> 1) ^ this.POLY) : (r >>> 1);
                r = r >>> 0;
            }
            this._TABLE[d] = r;
        }
    },

    crc32JsInt(data, signed = true) {
        this._ensureTable();
        let c = this.MASK32;
        const bytes = typeof data === 'string' ? stringToBytes(data) : data;
        for (const b of bytes) {
            c = (this._TABLE[((c & 0xFF) ^ b) & 0xFF] ^ (c >>> 8)) >>> 0;
        }
        let u = ((this.MASK32 ^ c) ^ this.POLY) >>> 0;
        if (signed && (u & 0x80000000)) {
            return u - 0x100000000;
        }
        return u;
    }
};

// ==================== 指纹生成 ====================
function generateFingerprint(cookies, userAgent) {
    const cookieString = Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join("; ");
    const screenConfig = getScreenConfig();
    const { vendor, renderer } = getRendererInfo();

    return {
        x1: userAgent, x2: "false", x3: "zh-CN",
        x4: weightedRandomChoice(FPData.COLOR_DEPTH_OPTIONS.values, FPData.COLOR_DEPTH_OPTIONS.weights),
        x5: weightedRandomChoice(FPData.DEVICE_MEMORY_OPTIONS.values, FPData.DEVICE_MEMORY_OPTIONS.weights),
        x6: "24", x7: `${vendor},${renderer}`,
        x8: weightedRandomChoice(FPData.CORE_OPTIONS.values, FPData.CORE_OPTIONS.weights),
        x9: `${screenConfig.width};${screenConfig.height}`,
        x10: `${screenConfig.availWidth};${screenConfig.availHeight}`,
        x11: "-480", x12: "Asia/Shanghai",
        x13: "true", x14: "true", x15: "true", x16: "false", x17: "false",
        x18: "un", x19: "Win32", x20: "", x21: FPData.BROWSER_PLUGINS,
        x22: md5(randomHex(32)),
        x23: "false", x24: "false", x25: "false", x26: "false", x27: "false",
        x28: "0,false,false", x29: "4,7,8", x30: "swf object not loaded",
        x33: "0", x34: "0", x35: "0", x36: String(randomInt(1, 20)),
        x37: "0|0|0|0|0|0|0|0|0|1|0|0|0|0|0|0|0|0|1|0|0|0|0|0",
        x38: "0|0|1|0|1|0|0|0|0|0|1|0|1|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0",
        x39: 0, x40: "0", x41: "0", x42: "3.4.4", x43: FPData.CANVAS_HASH,
        x44: String(Date.now()), x45: "__SEC_CAV__1-1-1-1-1|__SEC_WSA__|",
        x46: "false", x47: "1|0|0|0|0|0", x48: "", x49: "{list:[],type:}", x50: "", x51: "", x52: "",
        x55: "380,380,360,400,380,400,420,380,400,400,360,360,440,420",
        x56: `${vendor}|${renderer}|${md5(randomHex(32))}|35`,
        x57: cookieString, x58: "180", x59: "2", x60: "63", x61: "1291", x62: "2047",
        x63: "0", x64: "0", x65: "0",
        x66: { referer: "", location: "https://www.xiaohongshu.com/explore", frame: 0 },
        x67: "1|0", x68: "0", x69: "326|1292|30", x70: ["location"],
        x71: "true", x72: "complete", x73: "1191", x74: "0|0|0",
        x75: "Google Inc.", x76: "true", x77: "1|1|1|1|1|1|1|1|1|1",
        x78: { x: 0, y: 2400, left: 0, right: 290.828125, bottom: 2418, height: 18, top: 2400, width: 290.828125, font: FPData.FONTS },
        x82: "_0x17a2|_0x1954", x31: "124.04347527516074", x79: "144|599565058866",
        x53: md5(randomHex(32)), x54: FPData.VOICE_HASH_OPTIONS,
        x80: "1|[object FileSystemDirectoryHandle]"
    };
}

function generateB1(fp) {
    const b1Keys = ["x33", "x34", "x35", "x36", "x37", "x38", "x39", "x42", "x43", "x44", "x45", "x46", "x48", "x49", "x50", "x51", "x52", "x82"];
    const b1Fp = {};
    for (const k of b1Keys) {
        b1Fp[k] = fp[k];
    }
    const b1Json = JSON.stringify(b1Fp);
    const keyBytes = stringToBytes(CryptoConfig.B1_SECRET_KEY);
    const rc4 = new RC4(keyBytes);
    const jsonBytes = stringToBytes(b1Json);
    const ciphertext = rc4.encrypt(jsonBytes);

    // URL 编码
    let encoded = '';
    for (const byte of ciphertext) {
        if ((byte >= 0x41 && byte <= 0x5A) || (byte >= 0x61 && byte <= 0x7A) ||
            (byte >= 0x30 && byte <= 0x39) || "!*'()~_-".includes(String.fromCharCode(byte))) {
            encoded += String.fromCharCode(byte);
        } else {
            encoded += '%' + byte.toString(16).toUpperCase().padStart(2, '0');
        }
    }

    // 解析编码后的字符串
    const b = [];
    const parts = encoded.split('%').slice(1);
    for (const c of parts) {
        const chars = c.split('');
        b.push(parseInt(chars.slice(0, 2).join(''), 16));
        for (const j of chars.slice(2)) {
            b.push(j.charCodeAt(0));
        }
    }
    return base64Encode(new Uint8Array(b));
}

// ==================== 签名生成 ====================
function parseCookies(cookieStr) {
    const cookies = {};
    if (typeof cookieStr === 'object') return cookieStr;
    for (const pair of cookieStr.split(';')) {
        const [key, ...valueParts] = pair.trim().split('=');
        if (key) {
            cookies[key.trim()] = valueParts.join('=').trim();
        }
    }
    return cookies;
}

function extractUri(url) {
    const match = url.match(/^https?:\/\/[^\/]+(\/[^?#]*)/);
    if (match) return match[1];
    throw new Error(`Cannot extract URI from: ${url}`);
}

function buildContentString(method, uri, payload = null) {
    payload = payload || {};
    if (method.toUpperCase() === "POST") {
        return uri + JSON.stringify(payload);
    }
    if (Object.keys(payload).length === 0) {
        return uri;
    }
    const params = Object.entries(payload).map(([key, value]) => {
        let valStr;
        if (Array.isArray(value)) {
            valStr = value.join(',');
        } else if (value === null || value === undefined) {
            valStr = '';
        } else {
            valStr = String(value);
        }
        valStr = valStr.replace(/=/g, '%3D');
        return `${key}=${valStr}`;
    });
    return `${uri}?${params.join('&')}`;
}

function signXsCommon(cookieDict) {
    const a1Value = cookieDict.a1;
    const fingerprint = generateFingerprint(cookieDict, CryptoConfig.PUBLIC_USERAGENT);
    const b1 = generateB1(fingerprint);
    const x9 = CRC32.crc32JsInt(b1);

    const signStruct = { ...CryptoConfig.SIGNATURE_XSCOMMON_TEMPLATE };
    signStruct.x5 = a1Value;
    signStruct.x8 = b1;
    signStruct.x9 = x9;

    return base64Encode(JSON.stringify(signStruct));
}

function signXs(method, uri, a1Value, xsecAppid = "xhs-pc-web", payload = null, timestamp = null) {
    uri = extractUri(uri);
    const signatureData = { ...CryptoConfig.SIGNATURE_DATA_TEMPLATE };
    const contentString = buildContentString(method, uri, payload);
    const dValue = md5(contentString);

    const payloadArray = buildPayloadArray(dValue, a1Value, xsecAppid, contentString, timestamp);
    const xorResult = xorTransformArray(payloadArray);
    const x3Sig = base64EncodeX3(xorResult.slice(0, 124));

    signatureData.x3 = CryptoConfig.X3_PREFIX + x3Sig;
    return CryptoConfig.XYS_PREFIX + base64Encode(JSON.stringify(signatureData));
}

function getB3TraceId() {
    return randomHex(8);
}

function getXrayTraceId(timestampMs = null) {
    if (!timestampMs) timestampMs = Date.now();
    const tsHex = timestampMs.toString(16).padStart(12, '0').slice(0, 12);
    const seq = randomInt(0, 0x7FFFFF);
    const seqHex = seq.toString(16).padStart(5, '0');
    const randHex = randomHex(8).slice(0, 15);
    return tsHex + seqHex + randHex;
}

function signHeadersPost(uri, cookies, xsecAppid = "xhs-pc-web", payload = null, timestamp = null) {
    if (!timestamp) timestamp = Date.now() / 1000;
    const cookieDict = parseCookies(cookies);
    const a1Value = cookieDict.a1;
    if (!a1Value) throw new Error("Missing 'a1' in cookies");

    const xS = signXs("POST", uri, a1Value, xsecAppid, payload, timestamp);
    const xSCommon = signXsCommon(cookieDict);
    const xT = Math.floor(timestamp * 1000);

    return {
        "x-s": xS,
        "x-s-common": xSCommon,
        "x-t": String(xT),
        "x-b3-traceid": getB3TraceId(),
        "x-xray-traceid": getXrayTraceId(xT)
    };
}

function generateSignHeaders(cookie, noteId, xsecToken, xsecSource = "pc_user") {
    const apiUrl = "https://edith.xiaohongshu.com/api/sns/web/v1/feed";
    const payload = {
        source_note_id: noteId,
        image_formats: ["jpg", "webp", "avif"],
        extra: { need_body_topic: "1" },
        xsec_source: xsecSource,
        xsec_token: xsecToken
    };
    return signHeadersPost(apiUrl, cookie, "xhs-pc-web", payload);
}

// ==================== 采集核心逻辑 ====================
function extractNoteIdFromUrl(noteUrl) {
    noteUrl = noteUrl.trim();
    const patterns = [/\/explore\/([a-zA-Z0-9]+)/, /\/discovery\/item\/([a-zA-Z0-9]+)/];
    for (const pattern of patterns) {
        const match = noteUrl.match(pattern);
        if (match) return match[1];
    }
    throw new Error(`无法从 URL 中提取笔记 ID: ${noteUrl}`);
}

function extractQueryParam(noteUrl, key) {
    const match = noteUrl.match(new RegExp(`[?&]${key}=([^&]+)`));
    if (match) {
        return decodeURIComponent(match[1]);
    }
    return "";
}

function extractXsecTokenFromUrl(noteUrl) {
    return extractQueryParam(noteUrl, "xsec_token") || "";
}

function extractXsecSourceFromUrl(noteUrl) {
    return extractQueryParam(noteUrl, "xsec_source") || "";
}

async function fetchNoteDetail(noteId, xsecToken, xsecSource, cookie, userAgent) {
    const apiUrl = "https://edith.xiaohongshu.com/api/sns/web/v1/feed";
    const payload = {
        source_note_id: noteId,
        image_formats: ["jpg", "webp", "avif"],
        extra: { need_body_topic: "1" },
        xsec_source: xsecSource,
        xsec_token: xsecToken
    };

    console.log("[API] 生成签名...");
    const signHeaders = generateSignHeaders(cookie, noteId, xsecToken, xsecSource);
    console.log("[API] x-s 长度:", signHeaders["x-s"]?.length || 0);
    console.log("[API] x-t:", signHeaders["x-t"]);

    const headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": `https://www.xiaohongshu.com/explore/${noteId}`,
        "User-Agent": userAgent,
        "Cookie": cookie,
        ...signHeaders
    };

    console.log("[API] 发起请求...");
    const response = await fetch(apiUrl, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload)
    });

    console.log("[API] 响应码:", response.status);
    const responseText = await response.text();
    console.log("[API] 响应长度:", responseText.length);

    if (response.status === 406) {
        throw new Error("签名验证失败 (406)");
    }
    if (response.status !== 200) {
        throw new Error(`API 请求失败: HTTP ${response.status}`);
    }

    const data = JSON.parse(responseText);
    if (data.code === -100) {
        throw new Error("Cookie 已失效");
    }
    if (data.code !== 0) {
        throw new Error(`API 返回错误: ${data.msg || data.code}`);
    }

    console.log("[API] 请求成功 ✓");
    return data;
}

function processNoteDetail(feedData, noteId, xsecToken, xsecSource) {
    const items = feedData?.data?.items || [];
    if (items.length === 0) {
        throw new Error("响应中没有笔记数据");
    }

    const noteItem = items[0];
    const noteCard = noteItem.note_card || {};
    const user = noteCard.user || {};
    const interactInfo = noteCard.interact_info || {};
    const imageList = noteCard.image_list || [];
    const tagList = noteCard.tag_list || [];
    const video = noteCard.video || {};

    const imageText = imageList
        .map(img => img.url_default || img.url_pre || img.url || "")
        .filter(url => url)
        .join("\n");

    let coverUrl = "";
    if (noteCard.cover) {
        coverUrl = noteCard.cover.url_default || noteCard.cover.url_pre || noteCard.cover.url || "";
    }
    if (!coverUrl && imageList.length > 0) {
        coverUrl = imageList[0].url_default || imageList[0].url_pre || imageList[0].url || "";
    }

    const tagsArray = tagList
        .filter(tag => tag.type === "topic" && tag.name)
        .map(tag => tag.name);

    const videoUrl = video.origin_video_key || video.originVideoKey || video.url || "";
    const likedCount = parseInt(interactInfo.liked_count || 0) || 0;
    const collectedCount = parseInt(interactInfo.collected_count || 0) || 0;
    const commentCount = parseInt(interactInfo.comment_count || 0) || 0;
    const shareCount = parseInt(interactInfo.share_count || 0) || 0;
    const publishTime = noteCard.time || 0;

    const noteUrl = `https://www.xiaohongshu.com/explore/${noteId}?xsec_token=${xsecToken}&xsec_source=${xsecSource}`;
    const userNickname = user.nickname || user.nickName || user.nick_name || "";
    const userId = user.user_id || user.userId || "";
    const userAvatar = user.avatar || user.avatar_url || user.avatarUrl || "";
    const userHomePage = userId ? `https://www.xiaohongshu.com/user/profile/${userId}` : "";

    return {
        fields: {
            "图片链接": imageText,
            "笔记封面图链接": coverUrl,
            "笔记标题": noteCard.title || noteCard.display_title || "",
            "笔记内容": noteCard.desc || "",
            "笔记类型": noteCard.type || "",
            "笔记链接": noteUrl,
            "笔记标签": tagsArray,
            "账号名称": userNickname,
            "主页链接": userHomePage,
            "头像链接": userAvatar,
            "分享数": shareCount,
            "点赞数": likedCount,
            "收藏数": collectedCount,
            "评论数": commentCount,
            "视频链接": videoUrl,
            "发布时间": publishTime
        }
    };
}

// ==================== Coze 入口函数 ====================
async function main({ params }: Args): Promise<Output> {
    console.log("========== 开始采集 ==========");

    const noteUrl = (params.bijilianjie || params.note_url || params.noteUrl || "").trim();
    const cookie = (params.cookie || "").trim().replace(/\r/g, "").replace(/\n/g, "");

    console.log("URL长度:", noteUrl.length);
    console.log("Cookie长度:", cookie.length);

    if (!noteUrl || !cookie) {
        throw new Error("缺少必要参数");
    }
    if (!noteUrl.startsWith("http")) {
        throw new Error("链接格式不正确");
    }

    const userAgent = CryptoConfig.PUBLIC_USERAGENT;
    const noteId = extractNoteIdFromUrl(noteUrl);
    console.log("笔记ID:", noteId);

    let xsecToken = extractXsecTokenFromUrl(noteUrl).replace(/\s/g, "");
    const xsecSource = extractXsecSourceFromUrl(noteUrl) || "pc_user";

    if (!xsecToken) {
        throw new Error("链接缺少 xsec_token 参数");
    }

    console.log("Token长度:", xsecToken.length);

    const feedData = await fetchNoteDetail(noteId, xsecToken, xsecSource, cookie, userAgent);
    const record = processNoteDetail(feedData, noteId, xsecToken, xsecSource);

    console.log("标题:", record.fields["笔记标题"]);
    console.log("========== 采集完成 ✓ ==========");

    return {
        records: [record]
    };
}
