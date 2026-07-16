"""Compatibility entrypoint for the reproducible CIFAKE ResNet50 pipeline."""

from scripts.image_model_pipeline import parse_args, train, evaluate


if __name__ == "__main__":
    args = parse_args()
    train(args) if args.mode == "train" else evaluate(args)
