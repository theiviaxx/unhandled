import unhandled


conf = {
    'handlers': [
        unhandled.VerboseExceptionHandler,
        unhandled.SimpleExceptionHandler
    ]
}
unhandled.init()


def foo():
    f = 1
    print(f)
    1/0

# with unhandled.pause():
foo()
