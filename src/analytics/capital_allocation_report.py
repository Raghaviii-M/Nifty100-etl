ca = pd.read_csv(CA_CSV)
ca["yr"] = year_num(ca["year"])
print("rows per company (expect same for all):\n", ca.groupby("company_id").size().describe())
latest = ca[ca.yr == ca.yr.max()]
print(latest["pattern"].value_counts())                       # the 8 patterns, latest year

ca = ca.sort_values(["company_id", "yr"])
ca["previous_pattern"] = ca.groupby("company_id")["pattern"].shift()
changes = ca[ca.previous_pattern.notna() & (ca.previous_pattern != ca.pattern)]
changes[["company_id", "yr", "previous_pattern", "pattern"]].to_csv(
    OUT / "pattern_changes.csv", index=False)