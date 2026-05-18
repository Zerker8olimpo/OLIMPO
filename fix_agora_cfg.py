import json
from collections import Counter

def process():
    with open('backend/cfg/CFG_AGORA_PRODUCT_FAMILIES.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Detect duplicates
    all_fids = []
    for p in data['products']:
        for f in p.get('families', []):
            all_fids.append(f['family_id'])
    
    counts = Counter(all_fids)
    duplicates = {k for k, v in counts.items() if v > 1}
    
    seen = set()
    for p in data['products']:
        p_id = p['product_id']
        for f in p.get('families', []):
            fid = f['family_id']
            if fid in duplicates:
                if fid in seen:
                    # Modify the duplicate
                    if "construcción" in p_id:
                        f['family_id'] = fid + "_construccion"
                    elif "térmicos" in p_id:
                        f['family_id'] = fid + "_termicos"
                    else:
                        f['family_id'] = fid + "_alt"
                    f['review_notes'].append(f"ID modificado para evitar colision. Original: {fid}")
                seen.add(fid)
                
            # Fill missing fields
            f_name_lower = f['family_nombre'].lower()
            
            # attributes_for_matching
            if not f.get('attributes_for_matching'):
                if 'tubo' in f_name_lower or 'codo' in f_name_lower or 'tee' in f_name_lower:
                    f['attributes_for_matching'] = ['diametro', 'material', 'presion']
                elif 'cemento' in f_name_lower or 'mortero' in f_name_lower:
                    f['attributes_for_matching'] = ['rendimiento', 'material', 'aplicacion']
                else:
                    f['attributes_for_matching'] = ['formato', 'uso', 'material']
                    
            # exclude_terms
            if not f.get('exclude_terms'):
                exclude = []
                if 'tubo' in f_name_lower:
                    exclude.extend(['codo', 'tee', 'copla', 'valvula', 'pegamento'])
                elif 'codo' in f_name_lower or 'tee' in f_name_lower:
                    exclude.extend(['tubo', 'pegamento', 'valvula'])
                elif 'adhesivo' in f_name_lower or 'pegamento' in f_name_lower:
                    exclude.extend(['tubo', 'codo', 'ceramica'])
                if exclude:
                    f['exclude_terms'] = list(set(exclude))
                else:
                    f['exclude_terms'] = ['accesorio', 'repuesto', 'generico']
                    
            # normalization_notes
            if not f.get('normalization_notes'):
                if 'servicio' in f_name_lower or 'auditoria' in f_name_lower:
                    f['normalization_notes'] = ['Normalizar por operacion o proyecto']
                elif 'leche' in f_name_lower:
                    f['normalization_notes'] = ['Normalizar por litro']
                else:
                    f['normalization_notes'] = ['Normalizar por unidad estándar']
                    
    with open('backend/cfg/CFG_AGORA_PRODUCT_FAMILIES.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    process()
