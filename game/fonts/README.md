# Fonts

`MeadowBook.ttf` is Lora (variable weight, Copyright 2011 The Lora Project Authors) cut down to Latin letters and
punctuation (U+0020-007E, U+00A0-017F, U+2010-2027, U+2032-2033, U+20AC) and renamed, since the SIL Open Font
License (`OFL.txt`) keeps the name "Lora" for unchanged copies. Made with fontTools:

    python -m fontTools.subset Lora[wght].ttf --unicodes="U+0020-007E,U+00A0-017F,U+2010-2027,U+2032-2033,U+20AC"         --layout-features='kern,liga,calt' --output-file=Lora-latin.ttf

then name records 1, 3, 4 and 6 set to Meadow Book. The storybook uses it; other letters fall back to Godot's own font.
