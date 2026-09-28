import pytest

from supplygraph.evaluation.fixtures import truth_dataset


@pytest.fixture
def dataset():
    return truth_dataset()
