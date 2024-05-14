import { Popover, PopoverBody } from "react-bootstrap"

const HelpPopover = (
    <Popover>
        <PopoverBody>
            <div className="scroll">
                <h2>Format Specifiers</h2>
                <table className="bordered">
                    <thead>
                        <tr>
                            <th className="bordered">Specifier</th>
                            <th className="bordered">Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td className="bordered">%s</td>
                            <td className="bordered">The result is formatted as a string </td>
                        </tr>
                        <tr>
                            <td className="bordered">%d</td>
                            <td className="bordered">The result is formatted as a decimal integer </td>
                        </tr>
                        <tr>
                            <td className="bordered">%f</td>
                            <td className="bordered">The result is formatted as a decimal number</td>
                        </tr>
                        <tr>
                            <td className="bordered">%g</td>
                            <td className="bordered">The result is formatted using computerized scientific notation or decimal format, depending on the precision and the value after rounding. </td>
                        </tr>
                    </tbody>
                </table>
                <h2>HTML tags</h2>
                <table className="bordered">
                    <thead>
                        <tr>
                            <th className="bordered">Tag</th>
                            <th className="bordered">Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td className="bordered">&lt;b&gt;</td>
                            <td className="bordered">Bold</td>
                        </tr>
                        <tr>
                            <td className="bordered">&lt;i&gt;</td>
                            <td className="bordered">Italic</td>
                        </tr>
                        <tr>
                            <td className="bordered">&lt;u&gt;</td>
                            <td className="bordered">Underline</td>
                        </tr>
                        <tr>
                            <td className="bordered">&lt;u&gt;</td>
                            <td className="bordered">Underline</td>
                        </tr>
                        <tr>
                            <td className="bordered">&lt;font color=”hex_color”&gt;</td>
                            <td className="bordered">Setting font properties (verify on your system)</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </PopoverBody>
    </Popover>
)

export default HelpPopover