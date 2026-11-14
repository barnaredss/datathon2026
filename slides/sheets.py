import glob, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path
d = Path(__file__).resolve().parent / "preview"
fs = sorted(glob.glob(str(d / "Slide*.PNG")) + glob.glob(str(d / "Slide*.png")),
            key=lambda f: int(re.findall(r"(\d+)", Path(f).stem)[0]))
fs = list(dict.fromkeys(fs))
for k in range(0, len(fs), 6):
    fig, axs = plt.subplots(3, 2, figsize=(16, 13.5))
    for a in axs.ravel(): a.axis("off")
    for a, f in zip(axs.ravel(), fs[k:k + 6]):
        a.imshow(mpimg.imread(f)); a.set_title(Path(f).stem, fontsize=9)
    fig.tight_layout(pad=0.5)
    fig.savefig(d / f"sheet_{k // 6 + 1}.png", dpi=75); plt.close(fig)
print(len(fs))
