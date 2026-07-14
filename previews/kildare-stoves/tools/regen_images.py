"""Regenerate Kildare product images via Higgsfield image-to-image.

For each product that has a local real photo (assets/real/<id>.webp), generate a
soul_cinematic render conditioned on that photo (single --image-references), then
save a clean copy (assets/products_raw/<id>.webp) and a corner-marked copy
(assets/products/<id>.webp, what the site loads).

Usage:
    python regen_images.py test        # one product, end-to-end
    python regen_images.py all         # every product with a real photo
"""
import json, os, sys, io, time, subprocess, urllib.request
from PIL import Image, ImageDraw, ImageFont

BASE = r"D:\Midlands_Web\previews\kildare-stoves"
HF   = r"C:\Users\nojus\AppData\Roaming\npm\higgsfield.cmd"
REAL = os.path.join(BASE, "assets", "real")
OUT  = os.path.join(BASE, "assets", "products")
RAW  = os.path.join(BASE, "assets", "products_raw")
LOG  = os.path.join(BASE, "tools", "regen_log.txt")
os.makedirs(RAW, exist_ok=True)

def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

STYLE_SCENE = {
 "freestanding":"installed freestanding on a slate hearth in a warm, tastefully decorated modern Irish living room, a real wood fire glowing behind the glass door, a neat stack of logs beside it, soft natural window light",
 "pellet":"installed freestanding on a hearth in a warm modern Irish living room, a real fire glow behind the glass, soft natural light, cosy premium mood",
 "insert":"built into a brick fireplace recess beneath a timber mantel in a cosy modern Irish living room, a real fire glowing behind the glass, soft warm light",
 "cassette":"inset flush into a clean plastered fireplace wall in a minimalist modern Irish living room, a wide real fire glowing behind the glass, soft warm light",
 "electric":"freestanding in a modern living room with a realistic glowing flame effect, soft warm light, cosy",
 "boiler":"installed freestanding on a slate hearth in a warm modern Irish living space, a real fire glowing behind the glass, soft light",
}
def prompt_for(p):
    scene = STYLE_SCENE.get(p.get("style"), STYLE_SCENE["freestanding"])
    return (f"Editorial interior photograph of this exact {p['name']} stove, {scene}. "
            "Front-on, centred composition with the whole stove clearly visible and sharply in focus; "
            "warm cosy lighting but bright enough to clearly read the stove's shape, door and detail. "
            "Photorealistic, ultra detailed, premium lifestyle mood, no people, no text, no watermark, no logos.")

def hf(args, timeout=240):
    r = subprocess.run(["cmd", "/c", HF] + args, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr, r.returncode

def parse_job(out):
    data = json.loads(out)
    job = data[0] if isinstance(data, list) else data
    return job

def create_job(p):
    real = os.path.join(REAL, p["id"] + ".webp")
    out, err, rc = hf(["generate", "create", "soul_cinematic", "--prompt", prompt_for(p),
                       "--image-references", real, "--aspect-ratio", "4:3", "--json"])
    try:
        data = json.loads(out)
        if isinstance(data, list):
            first = data[0]
            return first if isinstance(first, str) else first.get("id")
        return data.get("id")
    except Exception:
        log(f"  CREATE FAIL {p['id']}: {(err or out)[:160]}")
        return None

def poll(job_id, tries=90, interval=8):
    for _ in range(tries):
        out, err, rc = hf(["generate", "get", job_id, "--json"])
        try:
            job = parse_job(out)
        except Exception:
            time.sleep(interval); continue
        st = job.get("status")
        if st == "completed":
            return job.get("result_url")
        if st in ("failed", "cancelled", "error"):
            log(f"  job {job_id} status={st}")
            return None
        time.sleep(interval)
    log(f"  job {job_id} timed out")
    return None

def font(sz):
    for p in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def process(pid, url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=90).read()
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    if w > 1400:
        img = img.resize((1400, int(h*1400/w)), Image.LANCZOS); w, h = img.size
    # clean copy
    img.save(os.path.join(RAW, pid + ".webp"), "WEBP", quality=88, method=6)
    # tasteful corner mark
    d = ImageDraw.Draw(img)
    f = font(int(w*0.026))
    label = "KILDARE STOVES"
    tw = d.textlength(label, font=f)
    padx, pady = int(w*0.035), int(h*0.065)
    d.text((w-tw-padx+2, h-pady+2), label, font=f, fill=(0,0,0))
    d.text((w-tw-padx, h-pady), label, font=f, fill=(255,224,186))
    img.save(os.path.join(OUT, pid + ".webp"), "WEBP", quality=88, method=6)

def run(products):
    log(f"=== creating {len(products)} jobs ===")
    jobs = {}
    for p in products:
        jid = create_job(p)
        if jid:
            jobs[p["id"]] = jid
            log(f"  created {p['id']} -> {jid}")
        time.sleep(1.0)
    log(f"=== {len(jobs)} jobs created; polling ===")
    done = 0
    for pid, jid in jobs.items():
        url = poll(jid)
        if not url:
            log(f"  NO RESULT {pid}"); continue
        try:
            process(pid, url); done += 1
            log(f"  saved {pid}  ({done}/{len(jobs)})")
        except Exception as e:
            log(f"  PROCESS FAIL {pid}: {str(e)[:160]}")
    log(f"=== DONE: {done}/{len(products)} images regenerated ===")

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    d = json.load(io.open(os.path.join(BASE, "data", "products.json"), encoding="utf-8"))
    realids = {os.path.splitext(f)[0] for f in os.listdir(REAL)}
    have = [p for p in d["products"] if p["id"] in realids]
    if mode == "test":
        run(have[:1])
    else:
        run(have)

if __name__ == "__main__":
    main()
