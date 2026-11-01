from datasets import load_dataset

ds = load_dataset("antoinejeannot/jurisprudence", "cour_de_cassation",
                  split="train", streaming=True)

first = next(iter(ds))
for col, val in first.items():
    print(f"{col:25} {str(val)[:100]!r}")