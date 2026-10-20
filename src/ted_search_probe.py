"""Read-only live TED Search contract probe. Prints aggregates, never raw notices."""
import json
from datetime import date, timedelta
from src.broker import ted_search
from src.ted_search_fields import apply_search_fields
from src.enrichment import enrich_opportunity
from src.public_opportunity_projection import project_public_opportunity

def main():
    end=date.today();start=end-timedelta(days=14)
    result=ted_search(f"publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}",25)
    rows=result.get("notices",result.get("results",[]))
    if not isinstance(rows,list) or not rows:
        raise RuntimeError("TED search did not return live notices")
    stats={"rows":len(rows),"single_lot":0,"multiple_lots":0,"unresolved_lots":0,"source_budgets":0,"official_notice_links":0,"budgets_preserved_through_dossier":0,"form_types":{}}
    for raw in rows:
        form=raw.get("form-type")
        if isinstance(form,list) and form and all(isinstance(v,str) for v in form) and len(set(form))==1:
            form=form[0]
        if not isinstance(form,str) or form not in {"bri","competition","completion","consultation","cont-modif","dir-awa-pre","planning","result"}:
            form="unknown"
        stats["form_types"][form]=stats["form_types"].get(form,0)+1
        row=apply_search_fields(dict(raw,source="TED"))
        count=row.get("ted_lot_count",0)
        stats["single_lot"]+=int(count==1)
        stats["multiple_lots"]+=int(count>1)
        stats["unresolved_lots"]+=int(count==0)
        stats["source_budgets"]+=int("estimated_value" in row)
        stats["official_notice_links"]+=int(bool(row.get("source_url")))
        amount=row.get("estimated_value")
        currency=row.get("budget_currency")
        enrich_opportunity(row)
        public=project_public_opportunity(row)
        if amount is not None:
            assert row["dossier"]["budget_value"]==amount
            assert row["dossier"]["budget_currency"]==currency
            assert public.get("estimated_budget")==amount
            assert public.get("budget_currency")==currency
            stats["budgets_preserved_through_dossier"]+=1
        if row.get("ted_lot_selection_required") is True:
            assert row["dossier"]["budget_value"] is None
            assert "estimated_budget" not in public
        assert "verified_unit_price" not in row and "verified_selling_unit_price" not in row
    print("TED_SEARCH_SOURCE_PROBE",json.dumps(stats,sort_keys=True))

if __name__=="__main__":
    main()
