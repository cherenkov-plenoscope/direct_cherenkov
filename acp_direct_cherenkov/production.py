"""
Usage: acp_direct_cherenkov -c=CONFIG -o=OUTPUT -e=EVTIO_EXTRACTOR

Options:
    -h --help                               Prints this help message.
    -c --config=CONFIG                      Path to the production config json 
                                            file.
    -o --output=OUTPUT                      Path of the output directory.
    -e --evtio_extractor=EVTIO_EXTRACTOR    Path to the mctracer eventio 
                                            extractor.
"""
import os
import shutil
import scoop
import docopt
import acp_direct_cherenkov as dc
import corsika_wrapper as cw
import tempfile
import subprocess


def eventio_extractor(eventio_path, output_path, eventio_extractor_path):
    with open(output_path+'.evtio_extractor.stdout', 'w') as out, open(output_path+'.evtio_extractor.stderr', 'w') as err:
        subprocess.call([
            eventio_extractor_path,
            '-i', eventio_path,
            '-o', output_path],
            stdout=out,
            stderr=err)   
          

def make_corsika_run(instruction):
    with tempfile.TemporaryDirectory(prefix='dc_production_') as tmp_dir:
        eventio_path = os.path.join(tmp_dir, 'corsika_run.evtio')

        cw.corsika(
            steering_card=instruction['corsika_steering_card'],
            output_path=eventio_path,
            save_stdout=True)

        shutil.copy(
            eventio_path+'.stdout', 
            instruction['output_path']+'.corsika.stdout')
        shutil.copy(
            eventio_path+'.stderr', 
            instruction['output_path']+'.corsika.stderr')

        eventio_extractor(
            eventio_path=eventio_path,
            output_path=instruction['output_path'],
            eventio_extractor_path=instruction['config']['evtio_extractor'])
    return True


def main():
    try:
        arguments = docopt.docopt(__doc__)

        # Set uo the output directory structure
        config = {}
        config['path'] = {}
        config['path']['main'] = {}
        config['path']['main']['dir'] = os.path.abspath(arguments['--output'])

        config['path']['main']['input'] = {}
        config['path']['main']['input']['dir'] = os.path.join(
            config['path']['main']['dir'],
            'input')

        os.mkdir(config['path']['main']['dir'])
        os.mkdir(config['path']['main']['input']['dir'])

        # Copy the steering card for this production
        config['path']['main']['input']['steering'] = os.path.join(
            config['path']['main']['input']['dir'],
            'steering.json')

        shutil.copy(
            arguments['--config'], 
            config['path']['main']['input']['steering'])

        # Copy the actual CORSIKA directory used for this simulation
        config['path']['main']['input']['corskia'] = os.path.join(
            config['path']['main']['input']['dir'],
            'corskia')

        shutil.copytree(
            dc.corsika_tools.corsika_directory(),
            config['path']['main']['input']['corskia'])

        # Read in the production steering
        config['steering'] = dc.steering.read_steering(
            config['path']['main']['input']['steering'])

        # Create the output directories for the different nuclei
        for nucleus in config['steering']['nuclei']:
            config['path']['main'][str(nucleus['PRMPAR'])] = os.path.join(
                config['path']['main']['dir'],
                dc.corsika_tools.PRMPAR_2_human_readable(nucleus['PRMPAR']))
            os.mkdir(config['path']['main'][str(nucleus['PRMPAR'])])

        # Set the mctracer eventio converter
        config['evtio_extractor'] = os.path.abspath(
            arguments['--evtio_extractor'])

        # Make the instructions and start parallel production
        instructions = dc.instructions.make_instructions(config)
        result = list(scoop.futures.map(make_corsika_run, instructions)) 

    except docopt.DocoptExit as e:        
        print(e)
  
if __name__ == '__main__':    
    main()