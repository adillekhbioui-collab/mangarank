"""
Step 8 - Deduplication Pipeline (three-layer matching).

Layers:
  1) Cross-reference ID matching (exact)
  2) Alternative title matching (high-threshold)
  3) Fuzzy primary title matching (fallback)

Output: pipeline/deduplicated.json
"""

import os
import re
import sys
import json
from collections import defaultdict
from rapidfuzz import fuzz

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

TITLE_FUZZY_THRESHOLD = 85
ALT_TITLE_FUZZY_THRESHOLD = 92
SOURCE_PRIORITY_TITLE = ["anilist", "mal", "mangadex", "kitsu"]
SOURCE_PRIORITY_AUTHOR = ["anilist", "mal", "mangadex", "kitsu"]
SOURCE_PRIORITY_COVER = ["mangadex", "anilist", "mal", "kitsu"]


class DisjointSet:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        return ""
    value = title.strip().lower()
    if not value:
        return ""
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def collect_titles(rec: dict) -> list[str]:
    titles = []
    primary = normalize_title(rec.get("title") or "")
    if primary:
        titles.append(primary)
    for alt in rec.get("alt_titles") or []:
        norm_alt = normalize_title(alt)
        if norm_alt:
            titles.append(norm_alt)
    # preserve order and unique
    seen = set()
    out = []
    for t in titles:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def is_likely_english(title: str) -> bool:
    if not isinstance(title, str):
        return False
    s = title.strip()
    if not s:
        return False
    ascii_chars = sum(1 for c in s if ord(c) < 128)
    ratio = ascii_chars / max(len(s), 1)
    letters = sum(1 for c in s if c.isalpha())
    return ratio >= 0.95 and letters >= 3


def build_components(records: list[dict], ds: DisjointSet) -> dict[int, list[int]]:
    comps: dict[int, list[int]] = defaultdict(list)
    for i in range(len(records)):
        comps[ds.find(i)].append(i)
    return dict(comps)


def count_multi_components(comps: dict[int, list[int]]) -> int:
    return sum(1 for idxs in comps.values() if len(idxs) > 1)


def chain_union(ds: DisjointSet, idxs: list[int]) -> int:
    if len(idxs) < 2:
        return 0
    merges = 0
    base = idxs[0]
    for i in idxs[1:]:
        if ds.union(base, i):
            merges += 1
    return merges


def normalize_external_id(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    clean = value.strip().lower()
    return clean or None


def build_source_token(source: str | None, external_id: str | None) -> str | None:
    src = (source or "").strip().lower()
    ext = normalize_external_id(external_id)
    if not src or not ext:
        return None
    return f"{src}:{ext}"


def layer1_id_matching(records: list[dict], ds: DisjointSet) -> int:
    """
    Layer 1 - Cross-reference ID matching.

    Uses mal_cross_id + MAL external_id as the primary exact bridge.
    """
    unions = 0

    token_to_record_indices: dict[str, list[int]] = defaultdict(list)
    mal_bridge_groups: dict[str, list[int]] = defaultdict(list)

    for i, rec in enumerate(records):
        source = rec.get("source_site") or ""
        ext_id = rec.get("external_id")
        mal_cross_id = (rec.get("mal_cross_id") or "").strip()
        source_token = build_source_token(source, ext_id)

        if source_token:
            token_to_record_indices[source_token].append(i)

        if source == "mal" and ext_id:
            mal_bridge_groups[str(ext_id).strip()].append(i)

        if mal_cross_id:
            mal_bridge_groups[mal_cross_id].append(i)

    # Step 1 + Step 2: AniList MAL bridge + externalLinks token graph.
    for i, rec in enumerate(records):
        if rec.get("source_site") != "anilist":
            continue

        candidate_idxs = [i]
        token_set = set()

        mal_cross_id = (rec.get("mal_cross_id") or "").strip()
        if mal_cross_id:
            token_set.add(f"mal:{mal_cross_id.lower()}")

        for token in rec.get("cross_link_ids") or []:
            if not isinstance(token, str):
                continue
            clean_token = token.strip().lower()
            if clean_token:
                token_set.add(clean_token)

        for token in token_set:
            candidate_idxs.extend(token_to_record_indices.get(token, []))

        # Deduplicate candidates while preserving order.
        deduped = []
        seen = set()
        for idx in candidate_idxs:
            if idx in seen:
                continue
            seen.add(idx)
            deduped.append(idx)

        unions += chain_union(ds, deduped)

    # Bridge any records sharing the same MAL cross-reference id.
    for _, idxs in mal_bridge_groups.items():
        unions += chain_union(ds, idxs)

    return unions


def layer2_alt_title_matching(records: list[dict], ds: DisjointSet) -> int:
    """
    Layer 2 - Alternative title matching for records still unmatched after layer 1.
    """
    unions = 0

    comps = build_components(records, ds)
    unmatched = [idxs[0] for idxs in comps.values() if len(idxs) == 1]
    if not unmatched:
        return unions

    titles_by_idx: dict[int, list[str]] = {i: collect_titles(records[i]) for i in unmatched}

    # Fast exact alt-title overlap first.
    title_index: dict[str, list[int]] = defaultdict(list)
    for i in unmatched:
        for t in titles_by_idx[i]:
            title_index[t].append(i)

    for _, idxs in title_index.items():
        # Avoid same-source-only merges.
        source_count = len(set(records[i].get("source_site") for i in idxs))
        if source_count < 2:
            continue
        unions += chain_union(ds, idxs)

    # Recompute unmatched after exact alt-title merges.
    comps = build_components(records, ds)
    unmatched = [idxs[0] for idxs in comps.values() if len(idxs) == 1]
    if not unmatched:
        return unions

    titles_by_idx = {i: collect_titles(records[i]) for i in unmatched}

    # Fuzzy alt-title match using simple blocking to avoid quadratic blowup.
    buckets: dict[tuple[str, int], list[int]] = defaultdict(list)
    processed = 0

    for i in unmatched:
        processed += 1
        if processed % 4000 == 0:
            print(f"    Layer 2 fuzzy progress: {processed}/{len(unmatched)}")

        source_i = records[i].get("source_site")
        titles_i = titles_by_idx.get(i, [])
        if not titles_i:
            # still add placeholder bucket for consistency
            continue

        candidate_ids: set[int] = set()
        for t in titles_i:
            key = (t[:1], len(t) // 5)
            for other in buckets.get(key, []):
                candidate_ids.add(other)

        for j in candidate_ids:
            if records[j].get("source_site") == source_i:
                continue

            titles_j = titles_by_idx.get(j, [])
            if not titles_j:
                continue

            matched = False
            for ta in titles_i:
                for tb in titles_j:
                    if fuzz.ratio(ta, tb) >= ALT_TITLE_FUZZY_THRESHOLD:
                        if ds.union(i, j):
                            unions += 1
                        matched = True
                        break
                if matched:
                    break

        for t in titles_i:
            key = (t[:1], len(t) // 5)
            buckets[key].append(i)

    return unions


def layer3_fuzzy_primary(records: list[dict], ds: DisjointSet) -> int:
    """
    Layer 3 - Fuzzy primary title matching for still-unmatched records.
    """
    unions = 0

    comps = build_components(records, ds)
    unmatched = [idxs[0] for idxs in comps.values() if len(idxs) == 1]
    if not unmatched:
        return unions

    primary = {i: normalize_title(records[i].get("title") or "") for i in unmatched}

    buckets: dict[tuple[str, int], list[int]] = defaultdict(list)
    processed = 0

    for i in unmatched:
        processed += 1
        if processed % 4000 == 0:
            print(f"    Layer 3 fuzzy progress: {processed}/{len(unmatched)}")

        source_i = records[i].get("source_site")
        t_i = primary.get(i, "")
        if not t_i:
            continue

        key = (t_i[:1], len(t_i) // 5)
        for j in buckets.get(key, []):
            if records[j].get("source_site") == source_i:
                continue
            t_j = primary.get(j, "")
            if not t_j:
                continue
            if fuzz.ratio(t_i, t_j) >= TITLE_FUZZY_THRESHOLD:
                if ds.union(i, j):
                    unions += 1
                    break

        buckets[key].append(i)

    return unions


def pick_by_source_priority(records: list[dict], field: str, priority: list[str]) -> str | None:
    by_source = defaultdict(list)
    for r in records:
        by_source[r.get("source_site")].append(r)

    for src in priority:
        for r in by_source.get(src, []):
            val = r.get(field)
            if isinstance(val, str) and val.strip():
                return val.strip()

    for r in records:
        val = r.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return None


def pick_canonical_title(records: list[dict]) -> str:
    # Prefer English-looking title from source priority among primary + alt titles.
    by_source = defaultdict(list)
    for r in records:
        by_source[r.get("source_site")].append(r)

    for src in SOURCE_PRIORITY_TITLE:
        for r in by_source.get(src, []):
            candidates = [r.get("title") or ""] + (r.get("alt_titles") or [])
            for cand in candidates:
                if isinstance(cand, str) and cand.strip() and is_likely_english(cand):
                    return cand.strip()

    # Fallback to primary titles by source priority.
    fallback = pick_by_source_priority(records, "title", SOURCE_PRIORITY_TITLE)
    if fallback:
        return fallback

    return (records[0].get("title") or "Unknown Title").strip() or "Unknown Title"


def merge_group(group_records: list[dict]) -> dict:
    title = pick_canonical_title(group_records)
    author = pick_by_source_priority(group_records, "author", SOURCE_PRIORITY_AUTHOR)

    genres = set()
    for r in group_records:
        for g in r.get("genres") or []:
            if isinstance(g, str) and g.strip():
                genres.add(g.strip().title())

    chapter_count = 0
    for r in group_records:
        try:
            value = int(r.get("chapter_count") or 0)
        except (TypeError, ValueError):
            value = 0
        if value > chapter_count:
            chapter_count = value

    cover_image = pick_by_source_priority(group_records, "cover_image", SOURCE_PRIORITY_COVER)

    statuses = [r.get("status") for r in group_records if r.get("status")]
    status = "completed" if statuses and all(s == "completed" for s in statuses) else "ongoing"

    # Keep source-level rating and popularity inputs for aggregate.py
    source_ratings = []
    for r in group_records:
        source_ratings.append({
            "source_site": r.get("source_site"),
            "rating": r.get("rating"),
            "rating_count": r.get("rating_count", 0),
            "view_count": r.get("view_count", 0),
            "summary": r.get("summary"),
            "count_current": r.get("count_current", 0),
            "count_completed": r.get("count_completed", 0),
            "count_dropped": r.get("count_dropped", 0),
            "count_paused": r.get("count_paused", 0),
            "count_planning": r.get("count_planning", 0),
        })

    merged_alt_titles = []
    seen_alt = set()
    for r in group_records:
        candidates = (r.get("alt_titles") or []) + [r.get("title") or ""]
        for cand in candidates:
            if not isinstance(cand, str):
                continue
            clean_cand = cand.strip()
            if not clean_cand:
                continue
            if clean_cand.lower() == title.strip().lower():
                continue
            key = clean_cand.lower()
            if key in seen_alt:
                continue
            seen_alt.add(key)
            merged_alt_titles.append(clean_cand)

    return {
        "title": title,
        "author": author,
        "genres": sorted(genres),
        "chapter_count": chapter_count,
        "cover_image": cover_image,
        "status": status,
        "alt_titles": merged_alt_titles,
        "source_ratings": source_ratings,
        "sources": sorted(set(r.get("source_site") for r in group_records if r.get("source_site"))),
    }


def print_merge_examples(
    records: list[dict],
    components: dict[int, list[int]],
    merged_by_root: dict[int, dict],
    limit: int = 10,
):
    print("\n  Example merged clusters")
    print("  " + "-" * 60)

    shown = 0
    for root, idxs in components.items():
        if len(idxs) < 2:
            continue
        parts = []
        for i in idxs:
            t = records[i].get("title") or "Unknown"
            s = records[i].get("source_site") or "unknown"
            parts.append(f'"{t}" ({s})')

        canonical = merged_by_root[root]["title"]
        print(f"  MERGED: {' + '.join(parts)}")
        print(f"          -> canonical: \"{canonical}\"")

        shown += 1
        if shown >= limit:
            break

    if shown == 0:
        print("  No multi-source merges found in this run.")


if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(__file__), "cleaned.json")
    output_path = os.path.join(os.path.dirname(__file__), "deduplicated.json")

    print("=" * 60)
    print("  Deduplication Pipeline (three-layer)")
    print("=" * 60)

    print("\n  Loading cleaned.json ...")
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    total_input = len(records)
    print(f"  Loaded {total_input} records")

    ds = DisjointSet(total_input)

    print("\n  Layer 1: Cross-reference ID matching ...")
    layer1_unions = layer1_id_matching(records, ds)
    comps1 = build_components(records, ds)
    id_matched_clusters = count_multi_components(comps1)
    print(f"    unions applied: {layer1_unions}")
    print(f"    multi-source clusters after layer 1: {id_matched_clusters}")

    print("\n  Layer 2: Alternative title matching ...")
    layer2_unions = layer2_alt_title_matching(records, ds)
    comps2 = build_components(records, ds)
    alt_total_clusters = count_multi_components(comps2)
    alt_added_clusters = max(0, alt_total_clusters - id_matched_clusters)
    print(f"    unions applied: {layer2_unions}")
    print(f"    additional clusters from alt titles: {alt_added_clusters}")

    print("\n  Layer 3: Fuzzy primary title matching ...")
    layer3_unions = layer3_fuzzy_primary(records, ds)
    comps3 = build_components(records, ds)
    fuzzy_total_clusters = count_multi_components(comps3)
    fuzzy_added_clusters = max(0, fuzzy_total_clusters - alt_total_clusters)
    print(f"    unions applied: {layer3_unions}")
    print(f"    additional clusters from fuzzy titles: {fuzzy_added_clusters}")

    # Merge all final components into canonical records.
    merged_records = []
    merged_by_root = {}
    for root, idxs in comps3.items():
        group = [records[i] for i in idxs]
        merged = merge_group(group)
        merged_records.append(merged)
        merged_by_root[root] = merged

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_records, f, indent=2, ensure_ascii=False)

    singles = sum(1 for idxs in comps3.values() if len(idxs) == 1)

    print_merge_examples(records, comps3, merged_by_root, limit=10)

    print("\n" + "=" * 60)
    print("  DEDUPLICATION SUMMARY")
    print("=" * 60)
    print(f"  Total input records:         {total_input}")
    print(f"  Matched via ID:              {id_matched_clusters} clusters")
    print(f"  Matched via alt titles:      {alt_added_clusters} additional clusters")
    print(f"  Matched via fuzzy matching:  {fuzzy_added_clusters} additional clusters")
    print(f"  Unmatched (single source):   {singles} records")
    print(f"  Total output unique manga:   {len(merged_records)}")
    print(f"  Saved to: {output_path}")
    print("=" * 60)
