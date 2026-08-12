/**
 * Generates the PWA manifest icons (192/512) into `web/icons/`.
 *
 * Produces brand-colored squares with a white "learning" mark (a simple
 * circle) using only Node built-ins, so the repository stays free of
 * binary assets that cannot be reviewed. Run with
 * `node scripts/generate_icons.mjs`.
 */
import { deflateSync } from 'node:zlib';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SIZES = [192, 512];
const BRAND = [0x2f, 0x6f, 0xed, 0xff]; // #2f6fed
const MARK = [0xff, 0xff, 0xff, 0xff]; // white mark
const OUT_DIR = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../web/icons',
);

/** Minimal PNG encoder (truecolor RGBA, no interlace). */
function encodePng(size, rgba) {
  const raw = Buffer.alloc(size * (size * 4 + 1));
  for (let y = 0; y < size; y++) {
    raw[y * (size * 4 + 1)] = 0; // filter: none
    for (let x = 0; x < size; x++) {
      const idx = y * (size * 4 + 1) + 1 + x * 4;
      raw[idx] = rgba[0];
      raw[idx + 1] = rgba[1];
      raw[idx + 2] = rgba[2];
      raw[idx + 3] = rgba[3];
    }
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // color type: RGBA

  const idat = deflateSync(raw);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', idat),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

function chunk(type, data) {
  const out = Buffer.alloc(8 + data.length + 4);
  out.writeUInt32BE(data.length, 0);
  out.write(type, 4, 'ascii');
  data.copy(out, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}

/** CRC-32 (IEEE 802.3) as used by PNG chunks. */
function crc32(buf) {
  let crc = 0xffffffff;
  for (const byte of buf) {
    crc ^= byte;
    for (let k = 0; k < 8; k++) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

/** True for pixels inside the white circle mark (radius 0.28, centered). */
function inMark(size, x, y) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.28;
  const dx = x - cx;
  const dy = y - cy;
  return dx * dx + dy * dy <= r * r;
}

mkdirSync(OUT_DIR, { recursive: true });
for (const size of SIZES) {
  const rgba = [];
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      rgba.push(...(inMark(size, x, y) ? MARK : BRAND));
    }
  }
  writeFileSync(resolve(OUT_DIR, `icon-${size}.png`), encodePng(size, rgba));
  console.log(`icon-${size}.png written`);
}
