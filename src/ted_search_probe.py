"""Read-only live TED Search contract probe. Prints aggregates, never raw notices."""
import json
from datetime import date, timedelta
from src.broker import ted_search
from src.ted_search_fields import apply_search_fields

def main():
    end=date.today();start=end-timedelta(days=14)
    result=ted_search(f"publication-date >= {start:%Y%m%d} AND publication-date <= {end:%Y%m%d}",25)
    rows=result.get("notices",result.get("results",[]))
    if not isinstance(rows,list) or not rows:
        raise RuntimeError("TED search did not return live notices")
    stats={"rows":len(rows),"single_lot":0,"multiple_lots":0,"unresolved_lots":0,"source_budgets":0,"official_notice_links":0}
    for raw in rows:
        row=apply_search_fields(dict(raw,source="TED"))
        count=row.get("ted_lot_count",0)
        stats["single_lot"]+=int(count==1)
        stats["multiple_lots"]+=int(count>1)
        stats["unresolved_lots"]+=int(count==0)
        stats["source_budgets"]+=int("estimated_value" in row)
        stats["official_notice_links"]+=int(bool(row.get("source_url")))
        assert "verified_unit_price" not in row and "verified_selling_unit_price" not in row
    print("TED_SEARCH_SOURCE_PROBE",json.dumps(stats,sort_keys=True))

if __name__=="__main__":
    main()
