




















Traceback (most recent call last):
  File "train.py", line 124, in <module>
    for bt, batchdata in enumerate(trainloader):
  File "/.autofs/tools/spack/opt/spack/linux-rhel7-x86_64/gcc-7.4.0/py-torch-1.2.0-fdksqtbpsau7tm3ql4lsmqej7rf5tgov/lib/python3.6/site-packages/torch/utils/data/dataloader.py", line 819, in __next__
    return self._process_data(data)
  File "/.autofs/tools/spack/opt/spack/linux-rhel7-x86_64/gcc-7.4.0/py-torch-1.2.0-fdksqtbpsau7tm3ql4lsmqej7rf5tgov/lib/python3.6/site-packages/torch/utils/data/dataloader.py", line 846, in _process_data
    data.reraise()
  File "/.autofs/tools/spack/opt/spack/linux-rhel7-x86_64/gcc-7.4.0/py-torch-1.2.0-fdksqtbpsau7tm3ql4lsmqej7rf5tgov/lib/python3.6/site-packages/torch/_utils.py", line 369, in reraise
    raise self.exc_type(msg)
OverflowError: Caught OverflowError in DataLoader worker process 4.
Original Traceback (most recent call last):
  File "/.autofs/tools/spack/opt/spack/linux-rhel7-x86_64/gcc-7.4.0/py-torch-1.2.0-fdksqtbpsau7tm3ql4lsmqej7rf5tgov/lib/python3.6/site-packages/torch/utils/data/_utils/worker.py", line 178, in _worker_loop
    data = fetcher.fetch(index)
  File "/.autofs/tools/spack/opt/spack/linux-rhel7-x86_64/gcc-7.4.0/py-torch-1.2.0-fdksqtbpsau7tm3ql4lsmqej7rf5tgov/lib/python3.6/site-packages/torch/utils/data/_utils/fetch.py", line 44, in fetch
    data = [self.dataset[idx] for idx in possibly_batched_index]
  File "/.autofs/tools/spack/opt/spack/linux-rhel7-x86_64/gcc-7.4.0/py-torch-1.2.0-fdksqtbpsau7tm3ql4lsmqej7rf5tgov/lib/python3.6/site-packages/torch/utils/data/_utils/fetch.py", line 44, in <listcomp>
    data = [self.dataset[idx] for idx in possibly_batched_index]
  File "/home/rsk3900/giw_e2e/CurriculumLib.py", line 92, in __getitem__
    elParam) if self.augFlag else (img,
  File "/home/rsk3900/giw_e2e/data_augment.py", line 76, in augment
    aug_base = cv2.line(aug_base, (x1, y1), (x2, y2), (255, 255, 255), 4)
OverflowError: signed integer is less than minimum
