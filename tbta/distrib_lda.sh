#!/bin/bash
python3 -m Pyro4.naming -n 0.0.0.0 &
python3 -m gensim.models.lda_dispatcher &
python3 -m gensim.models.lda_worker &
python3 -m gensim.models.lda_worker &
python3 -m gensim.models.lda_worker &
