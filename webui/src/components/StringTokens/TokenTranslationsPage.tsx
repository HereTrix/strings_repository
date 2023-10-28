import { ChangeEventHandler, FC, useState } from "react"
import StringToken from "../model/StringToken"
import { APIMethod, http } from "../Utils/network"
import TokenTranslation from "../model/TokenTranslation"
import { Button, ListGroup, Stack } from "react-bootstrap"
import OptionalImage from "../UI/OptionalImage"

type TokenTranslationsPageProps = {
    project_id: number
    token: StringToken
    open: boolean
}

type TokenTranslationsItemProps = {
    item: TokenTranslation
    onSave: (translation: string) => void
}

const TokenTranslationsItem: FC<TokenTranslationsItemProps> = ({ item, onSave }) => {

    const [canSave, setCanSave] = useState<boolean>(false)
    const [text, setText] = useState<string>(item.translation)

    const onTranslationChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
        setText(event.target.value)
        setCanSave(true)
    }

    const onSavePress = () => {
        setCanSave(false)
        onSave(text)
    }

    return (
        <ListGroup.Item
            className="d-flex justify-content-between align-items-start">
            <Stack>
                <Stack direction="horizontal" gap={2}>
                    <OptionalImage
                        src={`/static/flags/${item.code.toLocaleLowerCase()}.png`}
                        alt={item.code} />
                    <label>{item.code}</label>
                </Stack>
                <textarea
                    className="my-2"
                    defaultValue={item.translation}
                    onChange={onTranslationChange} />
                {canSave && <Button onClick={onSavePress} className="my-1">Save</Button>}
            </Stack>
        </ListGroup.Item>

    )
}

const TokenTranslationsPage: FC<TokenTranslationsPageProps> = ({ project_id, token, open }) => {

    const [translations, setTranslations] = useState<TokenTranslation[]>()

    const load = async () => {
        const result = await http<TokenTranslation[]>({
            method: APIMethod.get,
            path: `/api/string_token/${token.id}/translations`
        })

        if (result.value) {
            setTranslations(result.value)
        }
    }

    const saveTranslation = async (code: string, translation: string) => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/translation",
            data: { "project_id": project_id, "code": code, "token": token.token, "translation": translation }
        })

        if (result.error) {

        } else {

        }
    }

    if (open && !translations) {
        console.log("reload")
        load()
    }

    return (
        <ListGroup className="my-2">
            {translations &&
                translations.map((item) => <TokenTranslationsItem
                    item={item}
                    key={item.code}
                    onSave={(translation) => saveTranslation(item.code, translation)} />
                )}
        </ListGroup>
    )
}

export default TokenTranslationsPage