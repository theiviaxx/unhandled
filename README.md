#Unhandled

This is a simple lib to override default unhandled exceptions in python.  You can add different classes to different things based on the unhandled exception.

For example, we may want to add a jira issue for each unhandled exception.  However, we may want to ignore those exceptions coming from a console or some known developer space.  With this module, we can easily set that up or add any other handlers that may be useful.


### Installing

First get the module

```
pip install unhandled
```

To get it going, the api is similar to logging:

```
import unhandled

unhandled.basicConfig()

# OR

unhandled.basicConfig(['MyHandler', unhandled.VerboseExceptionHandler)
```

In this example you can provide a list of handlers either as strings, classes, or objects

## Versioning

I use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/theiviaxx/unhandled/tags).

## Authors

* **Brett Dixon** - *Initial work* - [theiviaxx](https://github.com/theiviaxx)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Django team for their work on the debug view
