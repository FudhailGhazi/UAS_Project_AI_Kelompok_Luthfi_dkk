import pandas as pd

color_map = {
    "Senin": "#E8F8F5",
    "Selasa": "#FDEDEC",
    "Rabu": "#FEF9E7",
    "Kamis": "#F4F6F7",
    "Jumat": "#F5EEF8",
    "Sabtu": "#FEF5E7"
}

def style_schedule_df(df):
    if "No" not in df.columns:
        df.insert(0, "No", range(1, len(df)+1))
    def row_color(row):
        hari = row["waktu"].split()[0] if isinstance(row["waktu"], str) else ""
        bg = color_map.get(hari, "")
        return [f"background-color: {bg}" for _ in row]
    sty = df.style.apply(row_color, axis=1)\
                  .set_properties(**{"text-align": "center", "padding": "6px"})\
                  .set_table_styles([{"selector":"th", "props":[("background-color","#2F4F4F"),("color","white"),("text-align","center")]}])
    return sty
