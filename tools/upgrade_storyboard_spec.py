#!/usr/bin/env python3
"""
升级 storyboard spec：添加 characters、char_ids、camera 拆分、mood 可视化、scene_anchors。
"""
import json
import re
import sys

def parse_camera(camera_str):
    """Parse camera string into shot_size, composition, camera_technique"""
    shot_size, composition, camera_technique = "", "", ""

    if 'close-up' in camera_str or 'close up' in camera_str:
        shot_size = "close-up"
    elif 'medium' in camera_str:
        shot_size = "medium"
    elif 'wide' in camera_str:
        shot_size = "wide"
    elif 'elevated' in camera_str or "bird's-eye" in camera_str or 'high angle' in camera_str:
        shot_size = "wide"
    elif 'macro' in camera_str:
        shot_size = "macro"

    if 'rule of thirds' in camera_str:
        composition = "rule of thirds"
    elif 'centered' in camera_str:
        composition = "centered"
    elif 'over-the-shoulder' in camera_str or 'over the shoulder' in camera_str:
        composition = "over-the-shoulder"
    elif 'eye-level' in camera_str or 'eye level' in camera_str:
        composition = "eye-level"
    elif 'two-shot' in camera_str or 'two shot' in camera_str:
        composition = "two-shot"
    elif 'front' in camera_str:
        composition = "frontal"
    elif 'behind' in camera_str or 'from behind' in camera_str:
        composition = "from-behind"

    if 'static' in camera_str:
        camera_technique = "static"
    elif 'dolly' in camera_str:
        camera_technique = "dolly-in" if 'dolly-in' in camera_str else "dolly"
    elif 'pan' in camera_str:
        camera_technique = "pan"
    elif 'zoom' in camera_str:
        camera_technique = "zoom"
    elif 'handheld' in camera_str:
        camera_technique = "handheld"
    elif 'slow motion' in camera_str or 'slow-motion' in camera_str:
        camera_technique = "slow-motion"
    elif '360' in camera_str or 'descending' in camera_str:
        camera_technique = "descending"
    elif 'ascending' in camera_str:
        camera_technique = "ascending"
    elif 'moving' in camera_str and 'handheld' not in camera_str:
        camera_technique = "tracking"
    elif 'cut' in camera_str.lower():
        camera_technique = "cutting"

    return shot_size, composition, camera_technique

def cleanup_scene(scene_str):
    """Remove redundant terms from scene description"""
    redundant_terms = [
        'neon-lit strip club', 'neon-lit neon-lit cabaret lounge', 'neon-lit cabaret lounge',
        'mid-tier neon-lit cabaret lounge', 'mid-tier strip club', 'two-story establishment',
        'stage with dramatic spotlights', 'velvet booth seating', 'mirror-tiled walls',
        'heavy haze from fog machine', 'bass-heavy pulsating music', 'warm humid air',
        'cigarette smoke', 'occasional applause', 'sensory overload'
    ]
    result = scene_str
    for term in sorted(redundant_terms, key=len, reverse=True):
        result = re.sub(re.escape(term), '', result, flags=re.IGNORECASE)
    result = re.sub(r',\s*,', ',', result)
    result = re.sub(r'\s+', ' ', result)
    result = result.strip().strip(',').strip()
    return result

def mood_to_visual(mood_str):
    """Convert abstract mood to visual/physical description"""
    mood_map = {
        'sensory overload': 'wide eyes, shoulders slightly back, taking in surroundings with visible awe',
        'excitement tinged with unease': 'slight tension in jaw, eyes bright but darting, body angled forward',
        'intoxicating allure': 'confident posture, commanding presence, fluid graceful movements',
        'dangerous magnetism': 'intense eye contact, predatory stillness, calculated charm',
        'moment of distraction': 'unfocused gaze, parted lips, leaning forward slightly',
        'increasingly frustrated': 'jaw tightening, fists loosening or clenching, eyes narrowing',
        'socially out of place': 'shoulders slightly hunched, avoiding eye contact, tentative hand gestures',
        'desperation building': 'rapid breathing visible, eyes darting, fidgeting hands, forced smile',
        'pragmatism': 'jaw set firm, direct eye contact, economical movements',
        'controlled aggression': 'tense shoulders, clenched fists, eyes cold and fixed',
        'acceptance of brute-force solution': 'deep sigh, nodding acceptance, straightening posture',
        'exhilaration': 'arms raised, face flushed with adrenaline, wide grin',
        'visual excess': 'head turning to follow falling money, eyes wide with wonder',
        'giddy power': 'laughing expression, loose shoulders, expansive arm movements',
        'controlled chaos': 'standing tall, scanning crowd, organized body language amidst mayhem',
        'sudden desertion': 'eyes tracking emptying space, visible relief, muscles relaxing',
        'opportunity': 'alert posture, eyes sharpening, moving forward with purpose',
        'window of vulnerability': 'poised but ready, coiled tension in legs',
        'cold analysis': 'eyes narrowed in focus, head perfectly still, calculating gaze',
        'tactical assessment': 'systematic eye movements, occasional finger pointing at targets',
        'controlled observation': 'minimal movement, breathing even and controlled, eyes methodical',
        'clinical disappointment': 'small head shake, pursed lips, controlled exhale',
        'tactical reset': 'straightening up, nodding decisively, eyes refocusing on next objective',
        'confrontational': 'chest forward, jaw tight, intense direct eye contact',
        'tense negotiation': 'leaning forward, hands gesturing carefully, eyes searching for reaction',
        'dangerous electricity': 'shallow breathing, stillness charged with tension',
        'cold transaction': 'flat expression, eyes tracking money, businesslike movements',
        'power play masked as negotiation': 'slight smile, controlled hand movements, eyes calculating',
        'survival instinct meeting desperation': 'eyes darting between speaker and money, fingers twitching',
        'triumph disguised as commerce': 'satisfied nod, slight smirk, relaxed posture',
        'liberation through payment': 'shoulders dropping, breathing easier, eyes less guarded',
        'dangerous knowledge': 'serious expression, leaning back, eyes hard and focused',
        'resolution': 'purposeful stride, eyes forward, shoulders relaxed but ready',
        'transition': 'looking between club and car, feet moving decisively',
        'anticipation of next phase': 'hands gripping door frame, eyes scanning ahead',
        'coiled tension': 'silence, minimal movement, eyes alert and tracking',
        'mutual assessment': 'calculating glances, body angled defensively, hands visible',
        'dangerous proximity': 'breath visible in the close space, stillness heavy with threat',
        'ugly pragmatism': 'expressionless face, mechanical movements, stripped of affect',
        'nowhere-ness': 'eyes looking at nothing in particular, posture slumped',
        'cutoff from the world': 'stillness, absence of natural movement, withdrawn expression',
        'transactional': 'mechanical gestures, eyes on money not on people, flat tone in face',
        'clinical': 'professional distance maintained in posture, minimal emotional expression',
        'stripped of pretense': 'hard eyes, straightforward body language, no artifice in stance',
        'existential concern': 'brow furrowed, eyes searching the other face intently',
        'mutual dependency': 'both leaning slightly forward, breath held, weighted silence',
        'final test of trust': 'long pause, eyes locked, no flinching',
        'dangerous knowledge exchanged': 'serious nod, eyes grave, weight settling into shoulders',
        'threshold crossed': 'visible change in posture, straightening up with finality',
        'point of no return reached': 'eyes closing briefly, deep breath, jaw set firm',
        'closure without satisfaction': 'nod of acceptance without smile, standing to leave',
        'transaction completed': 'straightening clothes, picking up belongings, eyes ahead',
        'moral ambiguity lingering': 'slight hesitation at door, glance back, conflicted expression'
    }

    mood_lower = mood_str.lower()
    for key, val in mood_map.items():
        if key.lower() == mood_lower:
            return val
    for key, val in mood_map.items():
        if key.lower() in mood_lower or mood_lower in key.lower():
            return val
    return mood_str

spec_path = 'specs/storyboard_main_plot_5h.spec.json'

with open(spec_path, 'r', encoding='utf-8') as f:
    spec = json.load(f)

panel_mapping = {
    'p01': ['X', 'Sergio', 'Elizabeth'],
    'p02': ['Elizabeth', 'X'],
    'p03': ['X'],
    'p04': ['X', 'Sergio'],
    'p05': ['X'],
    'p06': [],
    'p07': ['X'],
    'p08': ['X', 'Sergio'],
    'p09': ['X', 'Tony'],
    'p10': ['X', 'Tony'],
    'p11': ['X', 'Tony'],
    'p12': ['X', 'Tony', 'Sergio'],
    'p13': ['X', 'Sergio', 'Tony'],
    'p14': ['X', 'Sergio', 'Tony'],
    'p15': ['X', 'Sergio', 'Tony'],
    'p16': ['X', 'Sergio', 'Tony'],
    'p17': ['X', 'Sergio', 'Tony'],
    'p18': ['X', 'Sergio', 'Tony']
}

for panel in spec['panels']:
    panel_id = panel.get('panel_id')

    panel['char_ids'] = panel_mapping.get(panel_id, [])

    if 'scene' in panel:
        panel['scene'] = cleanup_scene(panel['scene'])

    if 'camera' in panel:
        shot_size, composition, camera_technique = parse_camera(panel['camera'])
        panel['shot_size'] = shot_size
        panel['composition'] = composition
        panel['camera_technique'] = camera_technique
        del panel['camera']

    if 'mood' in panel:
        panel['mood'] = mood_to_visual(panel['mood'])

spec['scene_anchors'] = {
    "club_stage": {"zone_name": "Main Stage Area", "zone_description": "Primary dance floor with chrome pole and dramatic tungsten spotlight isolation", "approved": False, "image_url": ""},
    "club_mezzanine": {"zone_name": "Mezzanine VIP Platform", "zone_description": "Elevated viewing platform with panoramic sightlines to dance floor and backstage", "approved": False, "image_url": ""},
    "club_backstage": {"zone_name": "Backstage / Dressing Area", "zone_description": "Cramped area with makeup stations, clothing racks, scattered seating", "approved": False, "image_url": ""},
    "car_interior": {"zone_name": "Vehicle Interior - Night", "zone_description": "Interior of car driving through neon-lit San Libre streets", "approved": False, "image_url": ""},
    "motel_exterior": {"zone_name": "Motel Exterior - Night", "zone_description": "Dingy mid-range motel with flickering neon vacancy sign, rain-slicked parking lot", "approved": False, "image_url": ""},
    "motel_room": {"zone_name": "Motel Room Interior", "zone_description": "Cramped room with worn carpet, two double beds, dim overhead light, drawn curtains", "approved": False, "image_url": ""}
}

with open(spec_path, 'w', encoding='utf-8') as f:
    json.dump(spec, f, ensure_ascii=False, indent=2)

print("✓ Spec upgraded")
print(f"✓ {len(spec['characters'])} characters")
print(f"✓ {len(spec['panels'])} panels updated")
print(f"✓ {len(spec['scene_anchors'])} scene_anchors added")
