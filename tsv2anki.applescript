set tsvPath to "/Users/cahrehn/dev/mtg2anki/tla.tsv"

openAnki()
importTsv(tsvPath)
selectNoteType()
setNoteType()

on openAnki()
	tell application "Anki"
		activate
		delay 5
	end tell
end openAnki

on importTsv(filePath)
	tell application "System Events"
		keystroke "i" using {shift down, command down}
		
		-- select/open the file
		keystroke "g" using {command down}
		delay 3
		# Type each character individually with a small delay
		repeat with i from 1 to length of filePath
			set currentChar to character i of filePath
			if currentChar is "." then
				key code 47
			else if currentChar is "2" then
				key code 19
			else
				keystroke currentChar
			end if
			delay 0.1
		end repeat
		delay 1
		keystroke return
		delay 0.5
		keystroke return
	end tell
end importTsv

on selectNoteType()
	tell application "System Events"
		-- Tab to the Note Type dropdown
		delay 2
		keystroke tab
		delay 0.5
		keystroke tab
		delay 0.5
		keystroke tab
		delay 0.5
		-- Open the dropdown
		keystroke space
		delay 2
	end tell
end selectNoteType

on setNoteType()
	set noteTypeTargetValue to "MTG Text Box"
	set noteTypeGroupNum to 9
	set numNoteTypes to my getItemCount(noteTypeGroupNum)
	set noteTypeTargetPosition to my getTargetPosition(noteTypeGroupNum, numNoteTypes, noteTypeTargetValue)
	my selectDropdownItem(numNoteTypes, noteTypeTargetPosition - 1)
end setNoteType

on selectDeck()
	tell application "System Events"
		keystroke tab
		delay 0.5
		keystroke space
		delay 0.5
	end tell
end selectDeck

on setDeck(deckName)
	set deckGroupNum to 11
	delay 1
	--	set numDeckTypes to my getItemCount(deckGroupNum)
	set numDeckTypes to 50
	set deckTargetPosition to my getTargetPosition(deckGroupNum, numDeckTypes, deckName)
	my selectDropdownItem(numDeckTypes, deckTargetPosition - 1)
end setDeck

on getTargetPosition(groupNum, itemCount, targetValue)
	tell application "System Events"
		tell process "Anki"
			tell window "Import File"
				set targetPosition to 0
				repeat with i from 1 to itemCount
					try
						set currentItem to static text i of menu button 1 of group 2 of group groupNum of group "csv import"
						set itemProps to properties of currentItem
						--						log "Item " & i & ": " & (title of itemProps)
						
						if (title of itemProps) is equal to targetValue then
							set targetPosition to i
						end if
						
					on error errMsg
						log "Error on item " & i & ": " & errMsg
					end try
					
					if (i mod 14) is equal to 0 then
						tell application "System Events"
							repeat (19) times
								key code 125 -- down arrow
								delay 0.1
							end repeat
						end tell
					end if
				end repeat
				return targetPosition
			end tell
		end tell
	end tell
end getTargetPosition


on getItemCount(groupNum)
	tell application "System Events"
		tell process "Anki"
			tell window "Import File"
				return count (static text of menu button 1 of group 2 of group groupNum of group "csv import")
			end tell
		end tell
	end tell
end getItemCount

on selectDropdownItem(numDropdownItems, targetPosition)
	tell application "System Events"
		repeat numDropdownItems times
			key code 126 -- up arrow
			delay 0.1
		end repeat
		
		repeat (targetPosition) times
			key code 125 -- down arrow
			delay 0.1
		end repeat
		
		keystroke return
	end tell
end selectDropdownItem
