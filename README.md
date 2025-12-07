# Description

This tool processes molecular dynamics (MD) trajectories to examine how ligands interact with their protein targets. It identifies and characterizes interaction types such as hydrogen bonds, hydrophobic contacts, and aromatic stacking, and presents the results through time-resolved visualizations. Multiple uploaded simulations can be used to create a group analysis. User can choose to provide experimental data to see the correlation between experiment outcomes and simulation results.

To reduce possible errrors, the tool tries to identify the protein as well as the ligand. Currently, it provides the SMILES and ChEBI ID for the ligand, and UniProt entry for the protein.

To see the website, follow [this link](https://coralmd.if-pan.krakow.pl/dashboard/).

# Installation
Start by cloning the repository:

```bash
git clone https://github.com/metro-maniana/CORAL-MD
```

To get the server running ASAP, do:
```bash
docker compose up
```
For development, do:
```bash
docker compose -f compose.yaml -f compose.admin.yaml up --build --watch --force-recreate --remove-orphans
```
To see the site, go to *localhost:8000*.

> [!WARNING]  
> You **NEED** to modify all the files inside the secrets directory, if the server is to be used for anything other than small testing.

> [!IMPORTANT]  
> Inside the .env file, you can configure some aspect of the website, if you plan to use it long-term, you should look through them.
