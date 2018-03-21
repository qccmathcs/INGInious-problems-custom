function load_input_custom(submissionid, key, input) {
    for(var entry in input) {
        if(entry.indexOf(key) !== -1) {
            if(entry in codeEditors) {
                if(entry in input)
                     codeEditors[entry].setValue(input[entry], -1);
                  else
                     codeEditors[entry].setValue("", -1);
                }
                else {
                    var field = $("input[name='" + entry + "']");
                    if (entry in input)
                        $(field).val(input[entry]);
                    else
                        $(field).val("");
                }
            }
    }
}

/**
 * Init a custom template
 * @param well: the DOM element containing the input fields
 * @param pid
 * @param problem
 */
function studio_init_template_custom(well, pid, problem)
{
    var val = "";
    if("boxes" in problem)
        val = JSON.stringify(problem["boxes"], null, 4);
    registerCodeEditor($('#boxes-' + pid)[0], 'json', 10).setValue(val);
}