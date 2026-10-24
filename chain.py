#!/usr/bin/env python3
"""Make the "I'm so sorry, I lied" chain from one photo with fal.ai (Nano Banana 2.1 edit).
Usage: FAL_KEY=... python chain.py photo.jpg --theme costume "lie 1" "lie 2" ["lie 3" ...]
"""
import argparse, base64, mimetypes, os, pathlib, re, sys, time
import requests

KEEP = ('Keep the same person with the exact same face, identity, age, expression, pose, framing, camera angle, '
        'background, lighting and photo quality. Do not change anything that is not listed. Do not add any text, '
        'letters, numbers or logos that are not already in the photo.')
THEME_RULE = {
    'costume': 'This is a Halloween costume photo. Make the costume a polished, store-quality version of the SAME costume theme and character. Never switch to a different costume or character.',
    'baby': 'This is a baby photo. Keep it the same baby at the same age.',
    'any': 'Keep the photo the same kind of photo.'}
THEME_KEEP = {'costume': 'This is a Halloween costume photo. Keep the same costume theme and character.', 'baby': THEME_RULE['baby'], 'any': THEME_RULE['any']}
HAIR = re.compile(r'\b(hair|haircut|curls?|curly|straight|wavy|bald|braids?|bangs|ponytail)\b', re.I)
HAIR_RULE = 'For hair, match the length and texture described exactly (straight means no curls or waves).'
MODEL = 'https://fal.run/google/nano-banana-2.1/edit'

def perfect_prompt(theme, lies):
    hair = f' {HAIR_RULE}' if any(HAIR.search(l) for l in lies) else ''
    return f"{KEEP} {THEME_RULE[theme]} Edit the photo so that all of these are true: {'; '.join(lies)}.{hair} Make each change look natural and believable, as if the photo had really been taken that way."

def retract_prompt(theme, lie, keep, with_original):
    first = 'the first' if with_original else 'this'
    ref = (' The second image is the original photo, for reference only: make that one detail look exactly as it does there '
           '(same materials, colors and shapes) and copy nothing else from it.') if with_original else ''
    stay = f" These must stay exactly as they are in {first} image: {'; '.join(keep)}." if keep else ''
    hair = f' {HAIR_RULE}' if HAIR.search(lie) else ''
    return f'Keep {first} image identical except one change: undo "{lie}" so that this is no longer true: {lie}.{ref}{stay} Do not alter anything else. {THEME_KEEP[theme]}{hair}'

def data_url(path):
    mime = mimetypes.guess_type(path)[0] or 'image/jpeg'
    return f'data:{mime};base64,' + base64.b64encode(pathlib.Path(path).read_bytes()).decode()

def edit(prompt, image_urls):
    r = requests.post(MODEL, headers={'Authorization': 'Key ' + os.environ['FAL_KEY']},
                      json={'prompt': prompt, 'image_urls': image_urls, 'num_images': 1, 'output_format': 'png'}, timeout=300)
    r.raise_for_status()
    return requests.get(r.json()['images'][0]['url'], timeout=120).content

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('photo'); ap.add_argument('lies', nargs='+'); ap.add_argument('--theme', default='any', choices=THEME_RULE)
    ap.add_argument('--out', default='out'); a = ap.parse_args()
    if 'FAL_KEY' not in os.environ: sys.exit('set FAL_KEY')
    out = pathlib.Path(a.out); out.mkdir(exist_ok=True); lies = [l.strip().rstrip('.! ') for l in a.lies]
    original = data_url(a.photo); prev = original
    for step in range(1, len(lies) + 1):
        if step == 1: prompt, imgs = perfect_prompt(a.theme, lies), [original]
        else:
            with_orig = a.theme == 'costume'
            prompt, imgs = retract_prompt(a.theme, lies[step - 2], lies[step - 1:], with_orig), [prev] + ([original] if with_orig else [])
        t = time.time(); png = edit(prompt, imgs); p = out / f'step-{step}.png'; p.write_bytes(png)
        prev = 'data:image/png;base64,' + base64.b64encode(png).decode()
        print(f'step {step}: {p} ({time.time() - t:.0f}s)')
    print(f'done. Slide {len(lies) + 1} is your original photo, untouched.')

if __name__ == '__main__':
    main()
