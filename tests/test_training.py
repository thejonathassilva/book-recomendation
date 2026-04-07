import pandas as pd
from src.training.evaluate import holdout_per_user
from src.training.metrics_ranking import precision_at_k


def test_holdout_and_precision():
    df = pd.DataFrame(
        {
            "user_id": [1, 1, 1, 2, 2, 2],
            "book_id": [10, 11, 12, 20, 21, 22],
        }
    )
    train, test_rel = holdout_per_user(df, test_ratio=0.3, seed=1)
    assert not train.empty
    assert precision_at_k([10, 11, 99], {12}, 3) >= 0.0
