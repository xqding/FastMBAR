"""
We run umbrella sampling for the butane dihedral (atom indices: 3-6-9-13).
The dihedral is split into multiple windows and in each window, the dihedral 
is restrainted around a center using a harmonic biasing potential. In this
script, we run simulations in each window sequentially, but they can be run in
parallel you have a computer cluster with multiple nodes.
"""

import simtk.openmm.app  as omm_app
import simtk.openmm as omm
import simtk.unit as unit
import math
import os
import numpy as np
from tqdm import tqdm
from sys import exit

## read the OpenMM system of dialanine
with open("./output/system.xml", 'r') as file_handle:
    xml = file_handle.read()    
system = omm.XmlSerializer.deserialize(xml)

## read psf and pdb file of dialanine
psf = omm_app.CharmmPsfFile("./data/dialanine.psf")
pdb = omm_app.PDBFile('./data/dialanine.pdb')

## setup an OpenMM context
platform = omm.Platform.getPlatformByName('CPU')
T = 298.15 * unit.kelvin
fricCoef = 10/unit.picoseconds
stepsize = 1 * unit.femtoseconds
integrator = omm.LangevinIntegrator(T, fricCoef, stepsize)
context = omm.Context(system, integrator, platform)

## set force constant for the biasing potential
k_psi = 100
k_phi = 100
context.setParameter("k_psi", k_psi)
context.setParameter("k_phi", k_phi)

## equilibrium value for both psi and phi in biasing potentials
M = 25
psi = np.linspace(-math.pi, math.pi, M, endpoint = False)
phi = np.linspace(-math.pi, math.pi, M, endpoint = False)

## the main loop to run umbrella sampling window by window
for idx in range(M**2):
    psi_index = idx // M
    phi_index = idx % M
    
    print(f"sampling at psi index: {psi_index} out of {M}, phi index: {phi_index} out of {M}")

    ## set the center of the biasing potential
    context.setParameter("psi", psi[psi_index])
    context.setParameter("phi", phi[phi_index])

    ## minimize 
    context.setPositions(pdb.positions)    
    state = context.getState(getEnergy = True)
    energy = state.getPotentialEnergy()
    for i in range(50):
        omm.LocalEnergyMinimizer_minimize(context, 1, 20)
        state = context.getState(getEnergy = True)
        energy = state.getPotentialEnergy()

    ## initial equilibrium
    integrator.step(5000)

    ## sampling production. trajectories are saved in dcd files
    file_handle = open(f"./output/traj/traj_psi_{psi_index}_phi_{phi_index}.dcd", 'bw')
    dcd_file = omm_app.dcdfile.DCDFile(file_handle, psf.topology, dt = stepsize)
    for i in tqdm(range(500)):
        integrator.step(200)
        state = context.getState(getPositions = True)
        positions = state.getPositions()
        dcd_file.writeModel(positions)    
    file_handle.close()
