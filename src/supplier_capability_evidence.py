"""Notice-bound, researched manufacturer capabilities; never full-spec approval."""
from __future__ import annotations

from copy import deepcopy

NOTICE = '681487-2026'
SOURCE = 'https://ted.europa.eu/en/notice/-/detail/681487-2026'
RESEARCH_DATE = '2026-10-19'

RECORDS = [
    {
        'name': 'FormFactor, Inc.',
        'source_url': 'https://www.formfactor.com/product/probe-systems/300-mm-systems/cm300xi-siph/',
        'identity_evidence_url': 'https://www.formfactor.com/company/about-us/',
        'product_match_evidence': 'Photonic wafer probe platform CM300xi-SiPh; optical probing with grating and edge coupling.',
        'identity_verification_evidence': 'Manufacturer company profile identifies FormFactor as a semiconductor test and measurement provider.',
        'product_scope': 'Photonic Wafer Probe Station',
        'capability_matches': [
            {'requirement': 'Optical grating coupling', 'capability': 'Vertical coupling to wafer-level grating couplers', 'evidence_url': 'https://www.formfactor.com/product/probe-systems/300-mm-systems/cm300xi-siph/'},
            {'requirement': 'Configurable edge coupling', 'capability': 'Wafer and die-level edge coupling with fibers and arrays', 'evidence_url': 'https://www.formfactor.com/product/probe-systems/300-mm-systems/cm300xi-siph/'},
            {'requirement': 'Optical and electrical characterization', 'capability': 'Optical automation combined with programmable DC and RF positioning', 'evidence_url': 'https://www.formfactor.com/product/probe-systems/autonomous-assistants/autonomous-silicon-photonics/'},
        ],
        'pending_requirements': ['RF up to 40 GHz in the offered configuration', 'Complete tender annex compliance and accessories', 'Supplier confirmation, delivery and quotation'],
    },
    {
        'name': 'ficonTEC Service GmbH',
        'source_url': 'https://www.ficontec.com/capabilities/',
        'identity_evidence_url': 'https://www.ficontec.com/imprint/',
        'product_match_evidence': 'Photonic assembly systems with active fiber alignment and edge-planar waveguide coupling.',
        'identity_verification_evidence': 'Official manufacturer site describes photonic device assembly and testing systems.',
        'product_scope': 'Photonic Assembly Station',
        'capability_matches': [
            {'requirement': 'Fiber-array attachment to optical chips', 'capability': 'Single and arrayed fiber pigtailing and active fiber alignment', 'evidence_url': 'https://www.ficontec.com/capabilities/'},
            {'requirement': 'Edge coupling alignment', 'capability': 'Fiber pigtailing for edge-planar waveguide coupling', 'evidence_url': 'https://www.ficontec.com/capabilities/'},
        ],
        'pending_requirements': ['Waveguide-loop alignment and two-FAU configuration', 'Complete tender annex compliance', 'Supplier confirmation, delivery and quotation'],
    },
]


def apply(row: dict) -> None:
    # Two independent source identifiers are required; never reuse by category.
    if row.get('source') != 'TED' or row.get('publication-number') != NOTICE:
        return
    title = str(row.get('title_original') or '').casefold()
    if not all(term in title for term in ('photonic wafer probe station', 'photonic assembly station')):
        return
    candidates = row.get('supplier_candidates')
    candidates = list(candidates) if isinstance(candidates, list) else []
    names = {str(c.get('name') or '').casefold() for c in candidates if isinstance(c, dict)}
    for record in RECORDS:
        if record['name'].casefold() not in names:
            candidate = deepcopy(record)
            candidate.update(researched_at=RESEARCH_DATE, notice_reference=NOTICE,
                             requirement_source_url=SOURCE, match_level='capability_only',
                             exact_spec_match=False, external_contact_authorized=False)
            candidates.append(candidate)
    row['supplier_candidates'] = candidates
