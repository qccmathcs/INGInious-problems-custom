# INGInious-problems-custom

Custom boxes INGInious problems.

## Installing

    pip3 install git+https://github.com/UCL-INGI/INGInious-problems-custom

## Activating

In your ``configuration.yaml`` file, add the following plugin entry:

    plugins:
      - plugin_module: "inginious-problems-custom"

## Usage

The following example prints an exercise where the students must complete the foor loop fields.
Boxes input are fetch using the following syntax : ``problemid/boxid``

    problems:
        problemid:
            type: custom
            header: Complete the for loop below.
            name: The for loop
            boxes:
                text1:
                    type: text
                    content: |-
                        .. raw:: html

                            <code>for(j=</code>
                for1:
                    type: input-integer
                    maxChars: 3
                text2:
                    type: text
                    content: |-
                        .. raw:: html

                            <code>; j <=</code>
                for2:
                    type: input-decimal
                    maxChars: 10
                text3:
                    type: text
                    content: |-
                        .. raw:: html

                            <code>;</code>
                for3:
                    type: input-text
                    maxChars: 10
                text4:
                    type: text
                    content: |-
                        .. raw:: html

                            <code>)</code>
                text5:
                    type: text
                    content: '``{``'
                for-content:
                    type: multiline
                    maxChars: 1000
                    lines: 5
                    language: python
                text6:
                    type: text
                    content: '``}``'
