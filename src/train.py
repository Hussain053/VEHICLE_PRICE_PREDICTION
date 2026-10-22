"""Compatibility entry point for the current eight-input model workflow."""


def main():
    from backend.train_model import main as train_eight_input_model

    return train_eight_input_model()


if __name__ == "__main__":
    main()
