import subprocess as sb
from pathlib import Path

import polars as pl
from lxml import objectify

INTERACTION_TYPES = [
    "hydrophobic_interaction",
    "hydrogen_bond",
    "halogen_bond",
    "salt_bridge",
    "pi_cation_interaction",
    "metal_complex",
    "water_bridge",
    "pi_stack",
]

LIGAND_TYPES = ["SMALLMOLECULE", "POLYMER", "DNA", "RNA", "ION"]

schema = pl.Schema(
    {
        "site_id": pl.Int64(),
        "int_type": pl.Enum(INTERACTION_TYPES),
        "lig_name": pl.String(),
        "lig_hetid": pl.String(),
        "lig_chain": pl.String(),
        "lig_pos": pl.Int64(),
        "lig_type": pl.Enum(LIGAND_TYPES),
        "res_name": pl.String(),
        "res_chain": pl.String(),
        "res_pos": pl.Int64(),
    }
)


def extract_plip_report(file: Path) -> pl.DataFrame:
    data = {
        "site_id": [],
        "int_type": [],
        "lig_name": [],
        "lig_hetid": [],
        "lig_chain": [],
        "lig_pos": [],
        "lig_type": [],
        "res_name": [],
        "res_chain": [],
        "res_pos": [],
    }
    root = objectify.parse(file).getroot()
    for site in root.bindingsite:
        for interaction_type in site.interactions.iterchildren():
            for interaction in interaction_type.iterchildren():
                data["site_id"].append(int(site.get("id")))
                data["int_type"].append(interaction.tag)
                data["lig_name"].append(site.identifiers.longname.text)
                data["lig_hetid"].append(site.identifiers.hetid.text)
                data["lig_chain"].append(site.identifiers.chain.text)
                data["lig_pos"].append(int(site.identifiers.position.text))
                data["lig_type"].append(site.identifiers.ligtype.text)
                data["res_name"].append(interaction.restype.text)
                data["res_chain"].append(interaction.reschain.text)
                data["res_pos"].append(int(interaction.resnr.text))

    return pl.DataFrame(data, schema=schema)


def run_plip(pdbfiles: list[Path], outdir: Path | None = None, worker_count: int = 1):
    processes = []
    # could be optimized
    for worker_idx in range(worker_count):
        pdbfiles_part = [
            pdbfile
            for i, pdbfile in enumerate(pdbfiles)
            if i % worker_count == worker_idx
        ]
        print(f"Starting plip instance with: {len(pdbfiles_part)} frames")
        if len(pdbfiles_part) == 0:
            continue
        process = sb.Popen(
            [
                "plip",
                "-v",
                "--nofix",
                "--nohydro",
                "-x",
                "-f",
            ]
            + pdbfiles_part,
            stdout=sb.PIPE,
            stderr=sb.STDOUT,
            text=True,
            bufsize=1,
            cwd=outdir,
        )
        processes.append(process)

    assert process.stdout is not None

    for worker_idx, process in enumerate(processes):
        stdout, _ = process.communicate()

        if process.returncode != 0:
            print(
                f"PLIP worker {worker_idx} failed (return code {process.returncode})",
                flush=True,
            )
            print(stdout)
    print("PLIP: Done!")
    return process.returncode == 0
