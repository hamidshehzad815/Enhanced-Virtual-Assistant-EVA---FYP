from pipeline.transformer_inputs import filter_model_inputs, pop_non_model_inputs


class _DistilStub:
    def forward(self, input_ids, attention_mask=None):
        return input_ids


class _BertStub:
    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        return input_ids


def test_filter_model_inputs_drops_token_type_ids_for_distilbert():
    model = _DistilStub()
    batch = {
        "input_ids": [1, 2],
        "attention_mask": [1, 1],
        "token_type_ids": [0, 0],
    }
    filtered = filter_model_inputs(model, batch)
    assert filtered == {"input_ids": [1, 2], "attention_mask": [1, 1]}


def test_filter_model_inputs_keeps_token_type_ids_for_bert():
    model = _BertStub()
    batch = {
        "input_ids": [1, 2],
        "attention_mask": [1, 1],
        "token_type_ids": [0, 0],
    }
    filtered = filter_model_inputs(model, batch)
    assert filtered == batch


def test_pop_non_model_inputs_mutates_batch():
    model = _DistilStub()
    batch = {
        "input_ids": [1],
        "attention_mask": [1],
        "token_type_ids": [0],
        "offset_mapping": [(0, 1)],
    }
    model_batch = pop_non_model_inputs(batch, model)
    assert model_batch == {"input_ids": [1], "attention_mask": [1]}
    assert "token_type_ids" not in batch
    assert "offset_mapping" not in batch
