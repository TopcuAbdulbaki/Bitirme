"""
SearchStrategy — Cycle başına arama sorgusu üretici.

Surface modda: önceden tanımlı çeşitleme şablonları
Research modda: mevcut bulgulara bakarak LLM'den dinamik sorgu üret
"""
from typing import List, Dict, Optional


class SearchStrategy:
    """Mevcut state'e göre arama sorgusu üretir."""

    # Surface modu için temel şablon listesi
    _SURFACE_TEMPLATES = [
        "{topic} news",
        "{topic} latest news",
        "{topic} breaking news",
        "{topic} today",
        "recent {topic} developments",
        "{topic} update",
        "{topic} headlines",
        "{topic} news analysis",
    ]

    # Research modu için ek şablon listesi (hipotez destekli)
    _RESEARCH_TEMPLATES = [
        "{topic}",
        "{topic} investigation",
        "{topic} analysis",
        "{topic} evidence",
        "{topic} report",
        "{topic} experts say",
        "{topic} fact check",
        "{topic} background",
        "{topic} timeline",
        "{topic} impact",
    ]

    @staticmethod
    def generate_queries(
        topic: str,
        mode: str,
        existing_findings: Optional[List[Dict]] = None,
        cycle: int = 0,
        current_hypothesis: str = "",
    ) -> List[str]:
        """
        Bir sonraki cycle için arama sorgularını üret.

        Args:
            topic:              Ana konu/arama terimi
            mode:               "surface" veya "research"
            existing_findings:  Önceki bulgular (anahtar kelime çıkarımı için)
            cycle:              Kaçıncı döngüde olduğumuz (çeşitleme için)
            current_hypothesis: Research modda mevcut hipotez metni

        Returns:
            Kullanılacak sorgu listesi (genelde 1-2 sorgu)
        """
        existing_findings = existing_findings or []

        if mode == "surface":
            return SearchStrategy._surface_queries(topic, cycle)
        else:
            return SearchStrategy._research_queries(
                topic, existing_findings, cycle, current_hypothesis
            )

    @staticmethod
    def _surface_queries(topic: str, cycle: int) -> List[str]:
        """
        Surface mod: şablon tabanlı çeşitleme.
        Her cycle farklı bir şablon kullanır.
        """
        templates = SearchStrategy._SURFACE_TEMPLATES
        idx = cycle % len(templates)
        # Her cycle 2 sorgu return et (birincil + alternatif)
        primary   = templates[idx].format(topic=topic)
        alt_idx   = (idx + 1) % len(templates)
        alternate = templates[alt_idx].format(topic=topic)
        return [primary, alternate]

    @staticmethod
    def _research_queries(
        topic: str,
        findings: List[Dict],
        cycle: int,
        hypothesis: str,
    ) -> List[str]:
        """
        Research mod: bulgulardan çıkarılan anahtar kelimeleri kullan.
        """
        # Temel şablon sorgular
        templates = SearchStrategy._RESEARCH_TEMPLATES
        idx       = cycle % len(templates)
        base_q    = templates[idx].format(topic=topic)
        queries   = [base_q]

        # Hipotez varsa onu da sorguya ekle
        if hypothesis and hypothesis not in ("No hypothesis yet", ""):
            # Hipotezden ilk 5 kelimeyi çıkar
            words = [w for w in hypothesis.split() if len(w) > 3][:5]
            if words:
                hypo_q = " ".join(words)
                queries.append(f"{topic} {hypo_q}")

        # Mevcut bulgulardan anahtar kelimeler çıkar
        keywords: set = set()
        for finding in findings[-4:]:  # Son 4 bulguya bak
            content = finding.get("content", "")
            title   = finding.get("title", "")
            # Başlıktan anlamlı kelimeleri al (5 harften uzun)
            for word in (title + " " + content[:500]).split():
                word = word.strip(".,;:!?\"'()[]").lower()
                if len(word) > 5 and word.isalpha():
                    keywords.add(word)

        # En fazla 2 keyword sorgusu ekle
        for kw in list(keywords)[:2]:
            queries.append(f"{topic} {kw}")

        # Duplicate kaldır, max 3 sorgı döndür
        seen = set()
        unique = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique.append(q)
        return unique[:3]

    @staticmethod
    def should_change_direction(
        findings: List[Dict], confidence: float, cycle: int
    ) -> bool:
        """
        Research modda yön değiştirmeli miyiz?
        Confidence durağanlaştıysa ve çok döngü geçtiyse evet.
        """
        return cycle > 3 and confidence < 0.3
