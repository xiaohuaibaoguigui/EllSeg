#!/bin/bash -l

path2ds="/home/rsk3900/Datasets/"
epochs=100
workers=9
batchsize=18
lr=0.0005

# Load necessary modules
spack load /7qmaaiw # Load OpenCV
spack load /jthz32l # Load pytorch by hash
spack load /dtlfq7l # Load torchvision by hash
spack load /fvki7dt # Load scipy
spack load /rso7arf # Load matplotlib
spack load /me57ozl # Load image manipulation library
spack load /bblye5g # Load sklearn for metrics
spack load /zzdgeg6 # Load tensorboardx (latest)
spack load /me75cc2 # Load tqdm
spack load /hlxw2mt # Load h5py with MPI

declare -a curObj_list=("0" "1" "2")
declare -a selfCorr_list=("0" "1")
declare -a disentangle_list=("0" "1")

for curObj in "${curObj_list[@]}"
do
    for selfCorr in "${selfCorr_list[@]}"
    do
        for disentangle in "${disentangle_list[@]}"
        do
            baseJobName="RC_e2e_${curObj}_${selfCorr}_${disentangle}"
            str="#!/bin/bash\npython3 train.py --path2data=${path2ds} --expname=${baseJobName} "
            str+="--curObj=${curObj} --batchsize=${batchsize} --workers=${workers} --prec=32 --epochs=${epochs} "
            str+="--disp=0 --overfit=0 --lr=${lr} --selfCorr=${selfCorr} --disentangle=${disentangle}"
            echo -e $str > command.lock
            sbatch -J ${baseJobName} -o "rc_log/${baseJobName}.o" -e "rc_log/${baseJobName}.e" --mem=16G --cpus-per-task=9 -p tier3 -A riteyes --gres=gpu:p4:2 -t 4-0:0:0 command.lock
        done
    done
done