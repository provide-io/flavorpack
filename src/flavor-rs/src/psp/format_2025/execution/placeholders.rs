//! Placeholder substitution utilities

use super::super::metadata::PackageInfo;
use log::warn;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Substitute placeholders in text
pub fn substitute_placeholders(text: &str, workenv_dir: &Path, package: &PackageInfo) -> String {
    let workenv_string;
    let workenv_str = if let Some(s) = workenv_dir.to_str() {
        s
    } else {
        warn!("Work environment path contains non-UTF8 characters, using lossy conversion");
        workenv_string = workenv_dir.to_string_lossy().into_owned();
        &workenv_string
    };
    text.replace("{workenv}", workenv_str)
        .replace("{package_name}", &package.name)
        .replace("{version}", &package.version)
}

/// Substitute `{slot:N}` with the extracted path of slot *N*.
///
/// Applied before [`substitute_placeholders`], matching the order the Go and
/// Python launchers use: a slot path may itself contain `{workenv}`, and the
/// basic substitution has to see it.
///
/// Paths are written with forward slashes. On Windows a backslash in a command
/// string is an escape to the shell that runs it, and the other two launchers
/// convert for the same reason.
///
/// An index with no extracted path is left as it stands, so an out-of-range
/// reference reaches the caller rather than being silently blanked.
pub fn substitute_slots(text: &str, slot_paths: &HashMap<usize, PathBuf>) -> String {
    if !text.contains("{slot:") {
        return text.to_string();
    }

    let mut out = text.to_string();
    for (index, path) in slot_paths {
        let replacement = path.to_string_lossy().replace('\\', "/");
        out = out.replace(&format!("{{slot:{index}}}"), &replacement);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn paths() -> HashMap<usize, PathBuf> {
        HashMap::from([
            (0, PathBuf::from("/workenv/data/payload.txt")),
            (1, PathBuf::from("/workenv/bin/tool")),
        ])
    }

    #[test]
    fn substitutes_each_slot_reference() {
        assert_eq!(
            substitute_slots("{slot:1} --input {slot:0}", &paths()),
            "/workenv/bin/tool --input /workenv/data/payload.txt"
        );
    }

    #[test]
    fn leaves_text_without_a_reference_alone() {
        assert_eq!(substitute_slots("/bin/true", &paths()), "/bin/true");
    }

    #[test]
    fn leaves_an_index_with_no_path_as_it_stands() {
        // The caller decides what an out-of-range reference means; blanking it
        // here would turn a broken command into a differently broken one.
        assert_eq!(substitute_slots("{slot:9}", &paths()), "{slot:9}");
    }

    #[test]
    fn writes_paths_with_forward_slashes() {
        let windows = HashMap::from([(0, PathBuf::from(r"C:\workenv\bin\tool"))]);
        assert_eq!(
            substitute_slots("{slot:0}", &windows),
            "C:/workenv/bin/tool"
        );
    }
}
