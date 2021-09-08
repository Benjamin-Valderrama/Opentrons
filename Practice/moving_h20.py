from opentrons import protocol_api
#from opentrons import simualte #opentrons_simulate.exe my_protocol.py

#Metadata
metadata = {
    'protocolName': 'My first protocol',
    'author': 'B. Valderrama>',
    'description': 'Simple protocol to get started using OT2',
    'apiLevel': '2.10'
}

#Protocol run
def run(protocol: protocol_api.ProtocolContext):
    
    ##Labware
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '9')
    samples = protocol.load_labware('nest_12_reservoir_15ml', '8')
    output = protocol.load_labware('nest_12_reservoir_15ml', '7')
    
    
    ##Pipettes
    pipette_20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks = [tiprack]) 
    
    
    ##Commands
    pipette_20.pick_up_tip()
    
    # Moving H20 from samples to output
    pipette_20.aspirate(5, samples['A1'])
    pipette_20.dispense(5, output['A1'])
    
    # Moving -OH from samples to output
    pipette_20.aspirate(2, samples['A12'])
    pipette_20.dispense(2, output['A2'])
    
    pipette_20.drop_tip()
