// Package shellparse provides shell-like command line parsing
// that correctly handles quoted arguments, spaces, and escapes.
//
// This is a minimal, dependency-free implementation inspired by POSIX shell
// word splitting rules, similar to Python's shlex.split() function.
package shellparse

import (
	"errors"
	"fmt"
	"strings"
	"unicode"
)

var (
	// ErrUnclosedQuote is returned when a quoted string is not properly closed
	ErrUnclosedQuote = errors.New("unclosed quote in command string")

	// ErrTrailingEscape is returned when a backslash appears at the end of input
	ErrTrailingEscape = errors.New("trailing escape character at end of command")
)

// Split parses a command string into arguments, handling quotes and escapes.
//
// Parsing rules:
//   - Words are separated by whitespace
//   - Single quotes preserve literal values (no escapes)
//   - Double quotes preserve literal values except for backslash escapes
//   - Backslash escapes the next character outside quotes
//   - Empty input returns empty slice
//
// Examples:
//
//	Split(`cmd arg1 arg2`) => ["cmd", "arg1", "arg2"]
//	Split(`cmd "arg with spaces"`) => ["cmd", "arg with spaces"]
//	Split(`cmd 'single quotes'`) => ["cmd", "single quotes"]
//	Split(`cmd arg\ with\ spaces`) => ["cmd", "arg with spaces"]
//	Split(`python -c "print('hello')"`) => ["python", "-c", "print('hello')"]
func Split(input string) ([]string, error) {
	if input == "" {
		return []string{}, nil
	}

	var result []string
	var current strings.Builder
	var inSingleQuote, inDoubleQuote bool
	var sawQuotes bool // Track if we've seen quotes for empty string handling

	runes := []rune(input)
	length := len(runes)

	for i := 0; i < length; i++ {
		ch := runes[i]

		// Handle escape sequences
		if ch == '\\' && !inSingleQuote {
			// Backslash escapes the next character (except in single quotes)
			if i+1 >= length {
				return nil, ErrTrailingEscape
			}
			i++
			nextCh := runes[i]

			// In double quotes, only escape special characters
			if inDoubleQuote {
				switch nextCh {
				case '"', '\\', '$', '`':
					current.WriteRune(nextCh)
				default:
					// Not a special char in double quotes, keep the backslash
					current.WriteRune('\\')
					current.WriteRune(nextCh)
				}
			} else {
				// Outside quotes, backslash escapes any character
				current.WriteRune(nextCh)
			}
			continue
		}

		// Handle single quotes
		if ch == '\'' && !inDoubleQuote {
			if inSingleQuote {
				// Closing single quote
				inSingleQuote = false
				sawQuotes = true
			} else {
				// Opening single quote
				inSingleQuote = true
			}
			continue
		}

		// Handle double quotes
		if ch == '"' && !inSingleQuote {
			if inDoubleQuote {
				// Closing double quote
				inDoubleQuote = false
				sawQuotes = true
			} else {
				// Opening double quote
				inDoubleQuote = true
			}
			continue
		}

		// Handle whitespace (word separators)
		if unicode.IsSpace(ch) && !inSingleQuote && !inDoubleQuote {
			// End current word if we have accumulated characters or saw quotes
			if current.Len() > 0 || sawQuotes {
				result = append(result, current.String())
				current.Reset()
				sawQuotes = false
			}
			continue
		}

		// Regular character - add to current word
		current.WriteRune(ch)
	}

	// Check for unclosed quotes
	if inSingleQuote || inDoubleQuote {
		quoteType := "single"
		if inDoubleQuote {
			quoteType = "double"
		}
		return nil, fmt.Errorf("%w: unclosed %s quote", ErrUnclosedQuote, quoteType)
	}

	// Add final word if present or if we saw quotes (empty quoted string)
	if current.Len() > 0 || sawQuotes {
		result = append(result, current.String())
	}

	return result, nil
}

// MustSplit is like Split but panics on error.
// This is useful for parsing static command strings that are known to be valid.
func MustSplit(input string) []string {
	result, err := Split(input)
	if err != nil {
		panic(fmt.Sprintf("shellparse.MustSplit: %v", err))
	}
	return result
}

// Join combines arguments into a shell command string, quoting as necessary.
// Arguments containing spaces, quotes, or special characters are quoted.
func Join(args []string) string {
	if len(args) == 0 {
		return ""
	}

	var parts []string
	for _, arg := range args {
		parts = append(parts, quote(arg))
	}

	return strings.Join(parts, " ")
}

// quote adds quotes around an argument if it contains special characters
func quote(arg string) string {
	if arg == "" {
		return "''"
	}

	// Check if quoting is needed
	needsQuote := false
	for _, ch := range arg {
		if unicode.IsSpace(ch) || ch == '\'' || ch == '"' || ch == '\\' || ch == '$' || ch == '`' {
			needsQuote = true
			break
		}
	}

	if !needsQuote {
		return arg
	}

	// Use single quotes if possible (simpler)
	if !strings.Contains(arg, "'") {
		return "'" + arg + "'"
	}

	// Use double quotes and escape special characters
	var result strings.Builder
	result.WriteRune('"')
	for _, ch := range arg {
		if ch == '"' || ch == '\\' || ch == '$' || ch == '`' {
			result.WriteRune('\\')
		}
		result.WriteRune(ch)
	}
	result.WriteRune('"')

	return result.String()
}
